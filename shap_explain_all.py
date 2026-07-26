"""
Genere l'explication SHAP (CPU et Memoire) pour tous les pods actifs
du namespace default, en une seule execution.
"""
from kubernetes import client, config
from shap_explain import explain_pod


def get_running_pods(namespace="default"):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace)
    return [p.metadata.name for p in pods.items if p.status.phase == "Running"]


def main():
    pods = get_running_pods()
    print(f"Generation des explications SHAP pour {len(pods)} pods...\n")

    for pod_name in pods:
        print("=" * 80)
        try:
            explain_pod(pod_name, namespace="default", target="cpu")
        except Exception as e:
            print(f"Erreur CPU pour {pod_name}: {e}")

        try:
            explain_pod(pod_name, namespace="default", target="mem")
        except Exception as e:
            print(f"Erreur Memoire pour {pod_name}: {e}")

    print("\n" + "=" * 80)
    print("Termine. Tous les graphiques .png sont dans le dossier courant.")


if __name__ == "__main__":
    main()
