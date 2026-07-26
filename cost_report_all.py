"""
Rapport economique complet pour tous les pods surveilles.
Combine les predictions ML en direct avec le calculateur de cout,
pour estimer l'economie potentielle sur l'ensemble du cluster.
"""
import requests
from kubernetes import client, config
from cost_calculator import calculer_economie, PRIX_VCPU_HEURE, PRIX_GB_RAM_HEURE

API_URL = "http://localhost:8000/predict"


def get_running_pods():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod("default")
    return [(p.metadata.name, p.metadata.namespace)
            for p in pods.items if p.status.phase == "Running"]


def get_current_allocation(pod_name, namespace):
    """Recupere les requests actuellement configurees sur K8s pour ce pod."""
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pod = v1.read_namespaced_pod(pod_name, namespace)
    container = pod.spec.containers[0]
    requests_res = container.resources.requests or {}

    cpu_str = requests_res.get("cpu", "0m")
    mem_str = requests_res.get("memory", "0Mi")

    cpu_m = int(cpu_str[:-1]) if cpu_str.endswith("m") else int(float(cpu_str) * 1000)
    if mem_str.endswith("Mi"):
        mem_mb = int(mem_str[:-2])
    elif mem_str.endswith("Gi"):
        mem_mb = int(float(mem_str[:-2]) * 1024)
    else:
        mem_mb = 0

    return cpu_m, mem_mb


def main():
    pods = get_running_pods()
    print(f"Analyse economique sur {len(pods)} pods actifs\n")

    header = f"{'Pod':<40} {'CPU actuel':<12} {'Economie/mois':<15} {'Economie/an':<15}"
    print(header)
    print("=" * len(header))

    total_mensuel = 0.0

    for pod_name, namespace in pods:
        try:
            resp = requests.post(API_URL, json={"pod": pod_name, "namespace": namespace}, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            cpu_reserve_actuel_m, mem_reserve_actuel_mb = get_current_allocation(pod_name, namespace)

            # Cout optimal théorique = prediction * marge (deja calculee par l'API)
            cpu_optimal_m = int(data["recommended_cpu_request"] * 1000)
            mem_optimal_mb = int(data["recommended_mem_request"] / (1024 * 1024))

            eco = calculer_economie(cpu_reserve_actuel_m, cpu_optimal_m,
                                     mem_reserve_actuel_mb, mem_optimal_mb)

            total_mensuel += eco["economie_mensuelle_usd"]

            print(f"{pod_name:<40} {cpu_reserve_actuel_m}m{'':<8} "
                  f"{eco['economie_mensuelle_usd']} USD{'':<5} "
                  f"{eco['economie_annuelle_usd']} USD")

        except Exception as e:
            print(f"{pod_name:<40} ERREUR: {e}")

    print("=" * len(header))
    print(f"\nECONOMIE TOTALE ESTIMEE : {round(total_mensuel, 2)} USD/mois "
          f"({round(total_mensuel * 12, 2)} USD/an)")
    print(f"\nHypotheses tarifaires : {PRIX_VCPU_HEURE} USD/vCPU/h, {PRIX_GB_RAM_HEURE} USD/Go RAM/h "
          f"(reference AWS On-Demand indicative)")


if __name__ == "__main__":
    main()
