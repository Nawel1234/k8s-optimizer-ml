# Kubernetes Intelligent Resource Optimizer

![CI Pipeline](https://github.com/Nawel1234/k8s-optimizer-ml/actions/workflows/ci.yml/badge.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![GitOps](https://img.shields.io/badge/gitops-argocd-orange)

Systeme d'optimisation autonome des ressources Kubernetes par apprentissage automatique (XGBoost).

---

## 📖 Contexte academique

Projet de Fin d'Etudes (PFE) — *Conception d'un systeme intelligent
d'optimisation predictive des ressources dans un cluster Kubernetes base
sur l'apprentissage automatique*.

**Auteur :** Nawel Dridi
**Annee :** 2026

---

## 📋 Table des matieres

- [Resultats cles](#-resultats-cles)
- [Architecture](#architecture)
- [Composants](#composants)
- [Performances du modele](#performances-du-modele)
- [Pipeline DevOps / GitOps](#pipeline-devops--gitops)
- [Installation](#installation)
- [Tests](#tests)
- [Deploiement Kubernetes](#deploiement-kubernetes-manuel-hors-gitops)
- [Fonctionnalites avancees](#fonctionnalites-avancees)
- [Limitations connues](#limitations-connues)

---

## 🎯 Resultats cles

| Metrique | Resultat |
|---|---|
| Reduction CPU (deployment de test) | **-98.8%** vs allocation initiale |
| Reduction RAM (deployment de test) | **-97.7%** vs allocation initiale |
| Precision modele CPU (R²) | 0.72 (MAPE 21%) |
| Precision modele Memoire (R²) | 0.99 (MAPE 5%) |
| Scaling automatique | Ajustement dynamique des replicas selon la charge predite |
| Autonomie | CronJob K8s toutes les 5 min, zero intervention manuelle |

---

## Architecture
## Composants

- `collector/` : collecte des metriques Prometheus
- `api/` : API FastAPI de prediction (modeles XGBoost entraines sur Kaggle)
- `optimizer/` : controleur d'optimisation automatique (requests/limits/replicas)
- `tests/` : tests unitaires (pytest)
- `.github/workflows/` : pipeline CI (tests + lint automatiques)
- `manifests/` : manifestes Kubernetes declaratifs (Deployment, Service, CronJob, RBAC)
- `Dockerfile` : image Docker multi-stage avec healthcheck
- `shap_explain.py` : explicabilite des predictions (SHAP)
- `cost_calculator.py` : traduction des gains en valeur economique

## Performances du modele

| Modele | R2 | MAPE |
|---|---|---|
| CPU | 0.72 | 21% |
| Memoire | 0.99 | 5% |

## Pipeline DevOps / GitOps
### Principe GitOps

Toute modification de configuration se fait via un commit sur ce depot.
ArgoCD detecte automatiquement le changement et synchronise le cluster
en consequence (`selfHeal: true`, `prune: true`), sans intervention manuelle.

### Deployer / mettre a jour via GitOps

```bash
git add manifests/
git commit -m "Description du changement"
git push
# ArgoCD synchronise automatiquement, aucune commande kubectl requise
```

### Acceder a ArgoCD
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

## Lancer l'API (mode local, hors cluster)

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Lancer l'Optimizer (mode local, hors cluster)

```bash
python3 optimizer/controller.py --namespace default
```

## Deploiement Kubernetes (manuel, hors GitOps)

```bash
kubectl apply -f manifests/rbac.yaml
kubectl apply -f manifests/api-deployment.yaml
kubectl apply -f manifests/optimizer-cronjob.yaml
```

## Construire l'image Docker

```bash
docker build -t k8s-optimizer-api:v1 .
```

## Fonctionnalites avancees

### Explicabilite du modele (SHAP)

```bash
python3 shap_explain.py <nom_du_pod> default cpu
```

### Estimation economique du gain

```bash
python3 cost_report_all.py
```

## Limitations connues

- Le modele CPU (R²=0.72) presente une precision plus modeste que le
  modele memoire (R²=0.99), consequence de la composante stochastique
  intrinseque des pics de charge CPU (variance irreductible).
- Le tarif utilise pour l'estimation economique est indicatif
  (reference AWS On-Demand) et doit etre adapte au fournisseur cloud
  reellement vise en production.
- `dex-server` (SSO externe d'ArgoCD) est desactive dans cet environnement
  en raison de restrictions reseau specifiques a l'infrastructure de test ;
  l'authentification admin locale reste pleinement fonctionnelle.
