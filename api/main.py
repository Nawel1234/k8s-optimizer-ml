"""
API de prediction - sert les modeles XGBoost entraines sur Kaggle.
"""

import sys
import os
from datetime import datetime

import numpy as np
import xgboost as xgb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    CPU_MODEL_PATH, MEM_MODEL_PATH,
    REQUEST_MARGIN, LIMIT_MARGIN,
)
from collector.prometheus_collector import PrometheusCollector
from fastapi import Response
from api.metrics import start_scheduler, get_metrics

app = FastAPI(
    title="K8s Intelligent Resource Optimizer - Prediction API",
    version="1.0.0",
)

collector = PrometheusCollector()

cpu_model = xgb.XGBRegressor()
mem_model = xgb.XGBRegressor()
_models_loaded = False


def load_models():
    global _models_loaded
    if os.path.exists(CPU_MODEL_PATH) and os.path.exists(MEM_MODEL_PATH):
        cpu_model.load_model(CPU_MODEL_PATH)
        mem_model.load_model(MEM_MODEL_PATH)
        _models_loaded = True
        print(f"Modeles charges: {CPU_MODEL_PATH}, {MEM_MODEL_PATH}")
    else:
        _models_loaded = False
        print(f"ATTENTION: modeles non trouves dans {CPU_MODEL_PATH}")


def _predict_for_scheduler(pod_name, namespace):
    """Wrapper reutilisant la logique de /predict pour le scheduler."""
    req = PredictionRequest(pod=pod_name, namespace=namespace)
    return predict(req)


@app.on_event("startup")
def startup_event():
    load_models()
    start_scheduler(_predict_for_scheduler, interval_seconds=30, namespace_filter=["default"])


class PredictionRequest(BaseModel):
    pod: str
    namespace: str = "default"


class PredictionResponse(BaseModel):
    pod: str
    namespace: str
    current_cpu_cores: float
    current_mem_bytes: float
    predicted_cpu_cores: float
    predicted_mem_bytes: float
    recommended_cpu_request: float
    recommended_cpu_limit: float
    recommended_mem_request: int
    recommended_mem_limit: int
    timestamp: str


def _pad_lags(hist, n=3):
    h = list(hist) if hist else [0.0]
    while len(h) < n + 1:
        h = [h[0]] + h
    return h[-1:-n-1:-1]


@app.get("/health")
def health():
    return {"status": "ok", "models_loaded": _models_loaded}


@app.get("/metrics")
def metrics():
    data, content_type = get_metrics()
    return Response(content=data, media_type=content_type)


@app.post("/predict", response_model=PredictionResponse)
def predict(req: PredictionRequest):
    if not _models_loaded:
        raise HTTPException(status_code=503, detail="Modeles non charges.")

    history = collector.get_recent_history(req.pod, req.namespace, points=5)
    cpu_hist = history["cpu_history"]
    mem_hist = history["mem_history"]

    current_cpu = cpu_hist[-1] if cpu_hist else 0.0
    current_mem = mem_hist[-1] if mem_hist else 0.0

    now = datetime.utcnow()
    hour = now.hour
    day_of_week = now.weekday()
    is_business_hour = 1 if 8 <= hour <= 19 else 0

    cpu_lags = _pad_lags(cpu_hist)
    mem_lags = _pad_lags(mem_hist)

    cpu_rolling_mean = float(np.mean(cpu_hist)) if cpu_hist else 0.0
    cpu_rolling_std = float(np.std(cpu_hist)) if len(cpu_hist) > 1 else 0.0
    mem_rolling_mean = float(np.mean(mem_hist)) if mem_hist else 0.0
    mem_rolling_std = float(np.std(mem_hist)) if len(mem_hist) > 1 else 0.0

    features = np.array([
        hour, day_of_week, is_business_hour,
        cpu_lags[0], cpu_lags[1], cpu_lags[2],
        cpu_rolling_mean, cpu_rolling_std,
        mem_lags[0], mem_lags[1], mem_lags[2],
        mem_rolling_mean, mem_rolling_std,
    ]).reshape(1, -1)

    # Predictions brutes du modele, SANS floor artificiel (transparence totale)
    predicted_cpu = max(float(cpu_model.predict(features)[0]), 0.0)
    predicted_mem = max(float(mem_model.predict(features)[0]), 0.0)

    recommended_cpu_request = round(predicted_cpu * REQUEST_MARGIN, 4)
    recommended_cpu_limit = round(predicted_cpu * LIMIT_MARGIN, 4)
    recommended_mem_request = int(predicted_mem * REQUEST_MARGIN)
    recommended_mem_limit = int(predicted_mem * LIMIT_MARGIN)

    return PredictionResponse(
        pod=req.pod,
        namespace=req.namespace,
        current_cpu_cores=round(current_cpu, 4),
        current_mem_bytes=int(current_mem),
        predicted_cpu_cores=round(predicted_cpu, 4),
        predicted_mem_bytes=int(predicted_mem),
        recommended_cpu_request=recommended_cpu_request,
        recommended_cpu_limit=recommended_cpu_limit,
        recommended_mem_request=recommended_mem_request,
        recommended_mem_limit=recommended_mem_limit,
        timestamp=datetime.utcnow().isoformat(),
    )
