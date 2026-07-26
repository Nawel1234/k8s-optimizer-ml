"""
Configuration centrale du projet Kubernetes Intelligent Resource Optimizer.
"""

import os

# --- Prometheus ---
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://192.168.44.191:30453")

# --- Kubernetes ---
KUBE_IN_CLUSTER = os.getenv("KUBE_IN_CLUSTER", "false").lower() == "true"
TARGET_NAMESPACE = os.getenv("TARGET_NAMESPACE", "default")

# --- Marges de securite appliquees par l'Optimizer ---
REQUEST_MARGIN = 1.2
LIMIT_MARGIN = 1.5

# --- Planchers minimum ---
MIN_CPU_CORES = 0.02
MIN_MEMORY_BYTES = 32 * 1024 * 1024

# --- Modeles ML ---
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
CPU_MODEL_PATH = os.path.join(MODEL_DIR, "xgb_cpu_model.json")
MEM_MODEL_PATH = os.path.join(MODEL_DIR, "xgb_mem_model.json")

# --- API ---
API_HOST = "0.0.0.0"
API_PORT = 8000
