"""
Module d'explicabilite du modele XGBoost via SHAP.
"""
import sys
import numpy as np
import xgboost as xgb
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

from collector.prometheus_collector import PrometheusCollector
from config.settings import CPU_MODEL_PATH, MEM_MODEL_PATH

FEATURE_NAMES = [
    "hour", "day_of_week", "is_business_hour",
    "cpu_lag_1", "cpu_lag_2", "cpu_lag_3", "cpu_rolling_mean", "cpu_rolling_std",
    "mem_lag_1", "mem_lag_2", "mem_lag_3", "mem_rolling_mean", "mem_rolling_std",
]


def pad_lags(hist, n=3):
    h = list(hist) if hist else [0.0]
    while len(h) < n + 1:
        h = [h[0]] + h
    return h[-1:-n-1:-1]


def build_features(pod_name, namespace, collector):
    history = collector.get_recent_history(pod_name, namespace, points=5)
    cpu_hist = history["cpu_history"]
    mem_hist = history["mem_history"]

    now = datetime.utcnow()
    hour = now.hour
    day_of_week = now.weekday()
    is_business_hour = 1 if 8 <= hour <= 19 else 0

    cpu_lags = pad_lags(cpu_hist)
    mem_lags = pad_lags(mem_hist)
    cpu_rolling_mean = float(np.mean(cpu_hist)) if cpu_hist else 0.0
    cpu_rolling_std = float(np.std(cpu_hist)) if len(cpu_hist) > 1 else 0.0
    mem_rolling_mean = float(np.mean(mem_hist)) if mem_hist else 0.0
    mem_rolling_std = float(np.std(mem_hist)) if len(mem_hist) > 1 else 0.0

    return np.array([[
        hour, day_of_week, is_business_hour,
        cpu_lags[0], cpu_lags[1], cpu_lags[2], cpu_rolling_mean, cpu_rolling_std,
        mem_lags[0], mem_lags[1], mem_lags[2], mem_rolling_mean, mem_rolling_std,
    ]])


def explain_pod(pod_name, namespace="default", target="cpu"):
    collector = PrometheusCollector()
    features = build_features(pod_name, namespace, collector)

    model = xgb.XGBRegressor()
    model.load_model(CPU_MODEL_PATH if target == "cpu" else MEM_MODEL_PATH)

    prediction = model.predict(features)[0]
    print(f"\n=== Explication de la prediction {target.upper()} pour '{pod_name}' ===")
    print(f"Valeur predite : {prediction:.4f}\n")

    # Fix compatibilite : on sauvegarde le modele sur disque, on corrige le
    # champ base_score dans le JSON brut, puis on recharge un Booster propre
    # a partir de ce fichier corrige (SHAP lit le dump JSON brut, pas la config
    # runtime, donc ce contournement est necessaire).
    import json as _json
    import tempfile
    import xgboost as _xgb

    tmp_path = tempfile.mktemp(suffix=".json")
    model.save_model(tmp_path)

    with open(tmp_path, "r") as f:
        _model_data = _json.load(f)
    _bs = _model_data["learner"]["learner_model_param"]["base_score"]
    if isinstance(_bs, str) and _bs.startswith("["):
        _model_data["learner"]["learner_model_param"]["base_score"] = _bs.strip("[]")
    with open(tmp_path, "w") as f:
        _json.dump(_model_data, f)

    clean_booster = _xgb.Booster()
    clean_booster.load_model(tmp_path)

    explainer = shap.TreeExplainer(clean_booster)
    shap_values = explainer.shap_values(features)

    print(f"{'Feature':<20} {'Valeur':<12} {'Contribution SHAP':<18} {'Impact'}")
    print("-" * 70)
    contributions = list(zip(FEATURE_NAMES, features[0], shap_values[0]))
    contributions.sort(key=lambda x: abs(x[2]), reverse=True)

    for name, val, shap_val in contributions:
        impact = "AUGMENTE" if shap_val > 0 else "DIMINUE"
        print(f"{name:<20} {val:<12.4f} {shap_val:<18.5f} {impact}")

    print(f"\nValeur de base (moyenne du modele) : {explainer.expected_value:.4f}")
    print(f"Somme (base + contributions) = prediction finale : "
          f"{explainer.expected_value + sum(shap_values[0]):.4f}")

    plt.figure(figsize=(10, 6))
    colors_bar = ["#d62728" if s > 0 else "#2ca02c" for _, _, s in contributions]
    names_sorted = [n for n, _, _ in contributions]
    values_sorted = [s for _, _, s in contributions]
    plt.barh(names_sorted[::-1], values_sorted[::-1], color=colors_bar[::-1])
    plt.xlabel("Contribution SHAP (impact sur la prediction)")
    plt.title(f"Explication de la prediction {target.upper()} — {pod_name}")
    plt.tight_layout()
    filename = f"shap_explanation_{target}_{pod_name.replace('/', '_')}.png"
    plt.savefig(filename, dpi=150)
    print(f"\nGraphique sauvegarde : {filename}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 shap_explain.py <nom_pod> [namespace] [cpu|mem]")
        sys.exit(1)

    pod = sys.argv[1]
    ns = sys.argv[2] if len(sys.argv) > 2 else "default"
    target = sys.argv[3] if len(sys.argv) > 3 else "cpu"

    explain_pod(pod, ns, target)
