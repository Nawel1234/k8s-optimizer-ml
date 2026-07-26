# Kubernetes Intelligent Resource Optimizer

![CI Pipeline](https://github.com/Nawel1234/k8s-optimizer-ml/actions/workflows/ci.yml/badge.svg)

Systeme d'optimisation autonome des ressources Kubernetes par apprentissage automatique (XGBoost).

## Architecture
Prometheus (metriques) -> Modele XGBoost (prediction) -> Optimizer Controller (patch K8s)

## Composants

- `collector/` : collecte des metriques Prometheus
- `api/` : API FastAPI de prediction (modeles XGBoost entraines sur Kaggle)
- `optimizer/` : controleur d'optimisation automatique (requests/limits/replicas)
- `tests/` : tests unitaires (pytest)
- `.github/workflows/` : pipeline CI (tests + lint automatiques)

## Performances du modele

| Modele | R2 | MAPE |
|---|---|---|
| CPU | 0.72 | 21% |
| Memoire | 0.99 | 5% |

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Tests

```bash
pytest tests/ -v
```

## Lancer l'API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Lancer l'Optimizer

```bash
python3 optimizer/controller.py --namespace default
```
