"""
Module d'exposition des metriques ML au format Prometheus.

Ce module maintient des Gauges Prometheus mises a jour periodiquement
avec les predictions du modele XGBoost pour chaque pod actif du cluster.
Prometheus scrape ensuite ces valeurs comme n'importe quelle autre metrique,
ce qui les rend visibles et graphables directement dans Grafana.
"""

from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from apscheduler.schedulers.background import BackgroundScheduler
from kubernetes import client, config
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Gauges Prometheus exposees ---
PREDICTED_CPU = Gauge(
    "ml_predicted_cpu_cores",
    "Charge CPU future predite par le modele XGBoost (en cores)",
    ["pod", "namespace"],
)
PREDICTED_MEM = Gauge(
    "ml_predicted_mem_bytes",
    "Charge memoire future predite par le modele XGBoost (en bytes)",
    ["pod", "namespace"],
)
CURRENT_CPU = Gauge(
    "ml_current_cpu_cores",
    "Usage CPU actuel observe au moment de la prediction (en cores)",
    ["pod", "namespace"],
)
CURRENT_MEM = Gauge(
    "ml_current_mem_bytes",
    "Usage memoire actuel observe au moment de la prediction (en bytes)",
    ["pod", "namespace"],
)
RECOMMENDED_CPU_REQUEST = Gauge(
    "ml_recommended_cpu_request_cores",
    "Recommandation CPU request calculee par l'Optimizer (en cores)",
    ["pod", "namespace"],
)
RECOMMENDED_MEM_REQUEST = Gauge(
    "ml_recommended_mem_request_bytes",
    "Recommandation memoire request calculee par l'Optimizer (en bytes)",
    ["pod", "namespace"],
)

_scheduler = None


def _get_target_pods(namespace_filter=None):
    """Recupere la liste des pods actifs a monitorer."""
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        pods = v1.list_pod_for_all_namespaces(watch=False)
        result = []
        for pod in pods.items:
            if pod.status.phase != "Running":
                continue
            if namespace_filter and pod.metadata.namespace not in namespace_filter:
                continue
            result.append((pod.metadata.name, pod.metadata.namespace))
        return result
    except Exception as e:
        print(f"Erreur recuperation pods: {e}")
        return []


def update_predictions_job(predict_fn, namespace_filter=None):
    """
    Job execute periodiquement : appelle la fonction de prediction
    pour chaque pod actif et met a jour les Gauges Prometheus.
    """
    pods = _get_target_pods(namespace_filter)
    for pod_name, namespace in pods:
        try:
            result = predict_fn(pod_name, namespace)
            PREDICTED_CPU.labels(pod=pod_name, namespace=namespace).set(result.predicted_cpu_cores)
            PREDICTED_MEM.labels(pod=pod_name, namespace=namespace).set(result.predicted_mem_bytes)
            CURRENT_CPU.labels(pod=pod_name, namespace=namespace).set(result.current_cpu_cores)
            CURRENT_MEM.labels(pod=pod_name, namespace=namespace).set(result.current_mem_bytes)
            RECOMMENDED_CPU_REQUEST.labels(pod=pod_name, namespace=namespace).set(result.recommended_cpu_request)
            RECOMMENDED_MEM_REQUEST.labels(pod=pod_name, namespace=namespace).set(result.recommended_mem_request)
        except Exception as e:
            print(f"Erreur prediction pour {pod_name}/{namespace}: {e}")


def start_scheduler(predict_fn, interval_seconds=30, namespace_filter=None):
    """Demarre le scheduler qui rafraichit les predictions periodiquement."""
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        lambda: update_predictions_job(predict_fn, namespace_filter),
        "interval",
        seconds=interval_seconds,
        id="ml_predictions_refresh",
    )
    _scheduler.start()
    print(f"Scheduler ML demarre (rafraichissement toutes les {interval_seconds}s)")


def get_metrics():
    """Retourne les metriques au format texte Prometheus."""
    return generate_latest(), CONTENT_TYPE_LATEST
