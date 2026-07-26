"""
Script de prediction sur tous les pods actifs du cluster.
Recupere dynamiquement la liste des pods via l'API Kubernetes
(pas de liste codee en dur, evite les noms obsoletes).
"""
import requests
from kubernetes import client, config


def get_running_pods():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces(watch=False)
    result = []
    for pod in pods.items:
        if pod.status.phase == "Running":
            result.append((pod.metadata.name, pod.metadata.namespace))
    return result


def predict_pod(pod_name, namespace):
    resp = requests.post(
        "http://localhost:8000/predict",
        json={"pod": pod_name, "namespace": namespace},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    pods = get_running_pods()
    print(f"Nombre de pods actifs detectes : {len(pods)}\n")

    header = f"{'POD':<45} {'NAMESPACE':<18} {'CPU_now':<9} {'CPU_pred':<9} {'MEM_now(MB)':<12} {'MEM_pred(MB)':<12}"
    print(header)
    print("=" * len(header))

    for pod_name, namespace in pods:
        try:
            data = predict_pod(pod_name, namespace)
            mem_now = data["current_mem_bytes"] / 1024 / 1024
            mem_pred = data["predicted_mem_bytes"] / 1024 / 1024
            print(f"{pod_name:<45} {namespace:<18} "
                  f"{data['current_cpu_cores']:<9} {data['predicted_cpu_cores']:<9} "
                  f"{mem_now:<12.1f} {mem_pred:<12.1f}")
        except Exception as e:
            print(f"{pod_name:<45} {namespace:<18} ERREUR: {e}")

    print("\nFini.")


if __name__ == "__main__":
    main()
