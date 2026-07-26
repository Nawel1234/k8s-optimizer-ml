"""
Optimizer Controller - applique automatiquement les recommandations
du modele ML sur les Deployments Kubernetes.
"""

import argparse
import json
import time
from datetime import datetime

import requests
from kubernetes import client, config

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import TARGET_NAMESPACE, KUBE_IN_CLUSTER, API_PORT

API_URL = f"http://localhost:{API_PORT}"
CHANGE_THRESHOLD_RATIO = 0.15

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "optimizer_actions.log")


def load_kube_config():
    if KUBE_IN_CLUSTER:
        config.load_incluster_config()
    else:
        config.load_kube_config()


def get_prediction(pod_name: str, namespace: str) -> dict:
    resp = requests.post(f"{API_URL}/predict", json={"pod": pod_name, "namespace": namespace}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def parse_cpu_to_cores(cpu_str) -> float:
    if cpu_str is None:
        return 0.0
    if cpu_str.endswith("m"):
        return float(cpu_str[:-1]) / 1000
    return float(cpu_str)


def parse_mem_to_bytes(mem_str) -> int:
    if mem_str is None:
        return 0
    units = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3}
    for suffix, factor in units.items():
        if mem_str.endswith(suffix):
            return int(float(mem_str[:-len(suffix)]) * factor)
    return int(mem_str)


def cores_to_cpu_str(cores: float) -> str:
    return f"{int(cores * 1000)}m"


def bytes_to_mem_str(n_bytes: int) -> str:
    return f"{int(n_bytes / (1024**2))}Mi"


def log_action(entry: dict):
    entry["timestamp"] = datetime.utcnow().isoformat()
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry, indent=2))


def calculate_target_replicas(current_replicas, predicted_cpu, current_cpu_request, min_replicas=1, max_replicas=5):
    """
    Calcule le nombre de replicas optimal selon la charge predite.
    Logique : si la charge predite depasse 80% de la capacite actuelle
    (replicas * request), on augmente. Si elle est sous 20%, on reduit.
    """
    if current_cpu_request <= 0:
        return current_replicas

    total_capacity = current_replicas * current_cpu_request
    utilization_ratio = predicted_cpu / total_capacity if total_capacity > 0 else 0

    if utilization_ratio > 0.8:
        target = min(current_replicas + 1, max_replicas)
    elif utilization_ratio < 0.2 and current_replicas > min_replicas:
        target = max(current_replicas - 1, min_replicas)
    else:
        target = current_replicas

    return target


def process_deployment(apps_v1, core_v1, deployment, namespace: str):
    name = deployment.metadata.name
    containers = deployment.spec.template.spec.containers
    if not containers:
        return

    container = containers[0]
    current_requests = container.resources.requests or {}

    current_cpu_req = parse_cpu_to_cores(current_requests.get("cpu"))
    current_mem_req = parse_mem_to_bytes(current_requests.get("memory"))

    pods = core_v1.list_namespaced_pod(namespace, label_selector=f"app={name}").items
    if not pods:
        pods = core_v1.list_namespaced_pod(namespace).items
        pods = [p for p in pods if name in p.metadata.name]
    if not pods:
        print(f"[SKIP] Aucun pod trouve pour le deployment {name}")
        return

    pod_name = pods[0].metadata.name

    try:
        prediction = get_prediction(pod_name, namespace)
    except requests.RequestException as e:
        print(f"[ERROR] Echec de la prediction pour {pod_name}: {e}")
        return

    new_cpu_req = prediction["recommended_cpu_request"]
    new_cpu_limit = prediction["recommended_cpu_limit"]
    new_mem_req = prediction["recommended_mem_request"]
    new_mem_limit = prediction["recommended_mem_limit"]

    cpu_change_ratio = abs(new_cpu_req - current_cpu_req) / max(current_cpu_req, 1e-6)

    if cpu_change_ratio < CHANGE_THRESHOLD_RATIO:
        print(f"[SKIP] {name}: ecart CPU {cpu_change_ratio:.1%} < seuil, pas de patch.")
        return

    current_replicas = deployment.spec.replicas or 1
    target_replicas = calculate_target_replicas(
        current_replicas, prediction["predicted_cpu_cores"], new_cpu_req
    )

    patch_body = {
        "spec": {
            "replicas": target_replicas,
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": container.name,
                            "resources": {
                                "requests": {
                                    "cpu": cores_to_cpu_str(new_cpu_req),
                                    "memory": bytes_to_mem_str(new_mem_req),
                                },
                                "limits": {
                                    "cpu": cores_to_cpu_str(new_cpu_limit),
                                    "memory": bytes_to_mem_str(new_mem_limit),
                                },
                            },
                        }
                    ]
                }
            }
        }
    }

    apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=patch_body)

    log_action({
        "deployment": name,
        "pod_reference": pod_name,
        "before": {
            "cpu_request": cores_to_cpu_str(current_cpu_req),
            "mem_request": bytes_to_mem_str(current_mem_req),
            "replicas": current_replicas,
        },
        "after": {
            "cpu_request": cores_to_cpu_str(new_cpu_req),
            "cpu_limit": cores_to_cpu_str(new_cpu_limit),
            "mem_request": bytes_to_mem_str(new_mem_req),
            "mem_limit": bytes_to_mem_str(new_mem_limit),
            "replicas": target_replicas,
        },
        "predicted_cpu_cores": prediction["predicted_cpu_cores"],
        "predicted_mem_bytes": prediction["predicted_mem_bytes"],
        "action": "PATCHED",
    })


def run_once(namespace: str):
    load_kube_config()
    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()

    deployments = apps_v1.list_namespaced_deployment(namespace).items
    print(f"{len(deployments)} deployment(s) trouve(s) dans le namespace '{namespace}'.")

    for dep in deployments:
        process_deployment(apps_v1, core_v1, dep, namespace)


def main():
    parser = argparse.ArgumentParser(description="Optimizer Controller")
    parser.add_argument("--namespace", default=TARGET_NAMESPACE)
    parser.add_argument("--interval", type=int, default=0)
    args = parser.parse_args()

    if args.interval <= 0:
        run_once(args.namespace)
    else:
        print(f"Optimizer Controller demarre en boucle (intervalle={args.interval}s)")
        while True:
            run_once(args.namespace)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
