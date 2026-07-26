#!/bin/bash
# Script de demonstration complete du PFE
# Kubernetes Intelligent Resource Optimizer

GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

pause() {
    echo ""
    read -p "Appuyez sur Entree pour continuer..."
    echo ""
}

clear
echo -e "${BOLD}${BLUE}"
echo "==============================================================="
echo "   KUBERNETES INTELLIGENT RESOURCE OPTIMIZER"
echo "   Demonstration complete - PFE"
echo "==============================================================="
echo -e "${NC}"
pause

# ============================================================
echo -e "${BOLD}${PURPLE}--- ETAPE 1 : Infrastructure du cluster ---${NC}"
echo ""
kubectl get nodes -o wide
echo ""
echo -e "${GREEN}Ci-dessus : les noeuds physiques/virtuels qui composent le cluster.${NC}"
pause

# ============================================================
echo -e "${BOLD}${PURPLE}--- ETAPE 2 : Applications actuellement deployees ---${NC}"
echo ""
kubectl get pods -n default -o wide
echo ""
echo -e "${GREEN}Ci-dessus : les applications (pods) surveillees par notre systeme.${NC}"
pause

# ============================================================
echo -e "${BOLD}${PURPLE}--- ETAPE 3 : Consommation reelle (Metrics Server) ---${NC}"
echo ""
kubectl top pods -n default
echo ""
echo -e "${GREEN}Ci-dessus : ce que chaque application consomme VRAIMENT en ce moment.${NC}"
pause

# ============================================================
echo -e "${BOLD}${PURPLE}--- ETAPE 4 : Sante de l'API de prediction ML ---${NC}"
echo ""
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""
echo -e "${GREEN}Confirmation : le modele XGBoost est charge et pret a predire.${NC}"
pause

# ============================================================
echo -e "${BOLD}${PURPLE}--- ETAPE 5 : PREDICTION EN DIRECT sur toutes les applications ---${NC}"
echo ""
python3 predict_all.py
echo ""
echo -e "${GREEN}Ci-dessus : pour chaque pod, le modele compare l'usage actuel, la prediction,${NC}"
echo -e "${GREEN}et calcule automatiquement les requests/limits recommandes.${NC}"
pause

# ============================================================
echo -e "${BOLD}${PURPLE}--- ETAPE 6 : Ressources AVANT optimisation (etat actuel Kubernetes) ---${NC}"
echo ""
for pod_name in $(kubectl get deployments -n default -o jsonpath='{.items[*].metadata.name}'); do
    echo -e "${YELLOW}Deployment: $pod_name${NC}"
    kubectl get deployment "$pod_name" -n default -o jsonpath='{.spec.template.spec.containers[0].resources}'
    echo ""
done
pause

# ============================================================
echo -e "${BOLD}${PURPLE}--- ETAPE 7 : LANCEMENT DE L'OPTIMIZER (decision automatique) ---${NC}"
echo -e "${YELLOW}L'Optimizer va maintenant interroger le modele ML pour chaque deployment${NC}"
echo -e "${YELLOW}et ajuster automatiquement requests, limits et replicas.${NC}"
echo ""
python3 optimizer/controller.py --namespace default
echo ""
pause

# ============================================================
echo -e "${BOLD}${PURPLE}--- ETAPE 8 : Ressources APRES optimisation (verification) ---${NC}"
echo ""
for pod_name in $(kubectl get deployments -n default -o jsonpath='{.items[*].metadata.name}'); do
    echo -e "${YELLOW}Deployment: $pod_name${NC}"
    kubectl get deployment "$pod_name" -n default -o jsonpath='{.spec.template.spec.containers[0].resources}'
    echo ""
done
pause

# ============================================================
echo -e "${BOLD}${PURPLE}--- ETAPE 9 : Rapport chiffre du gain obtenu ---${NC}"
echo ""
python3 generate_report.py
echo ""
pause

# ============================================================
echo -e "${BOLD}${PURPLE}--- ETAPE 10 : Traduction du gain en valeur economique ---${NC}"
echo ""
echo -e "${YELLOW}Conversion des ressources economisees en estimation de cout cloud${NC}"
echo -e "${YELLOW}(tarification indicative de reference, ex: AWS On-Demand).${NC}"
echo ""
python3 cost_report_all.py
echo ""
pause

# ============================================================
echo -e "${BOLD}${PURPLE}--- ETAPE 11 : Explicabilite du modele (SHAP) ---${NC}"
echo ""
echo -e "${YELLOW}Le modele ne se contente pas de predire : il justifie chaque${NC}"
echo -e "${YELLOW}decision individuelle grace a l'explicabilite SHAP.${NC}"
echo ""
read -p "Entrez le nom exact d'un pod a expliquer (ex: carts-demo-xxxxx) : " pod_a_expliquer
python3 shap_explain.py "$pod_a_expliquer" default cpu
echo ""
echo -e "${GREEN}Graphique d'explication genere. Consultez-le via :${NC}"
echo -e "${GREEN}  cd ~/k8s-optimizer-ml && python3 -m http.server 8899${NC}"
echo -e "${GREEN}  puis ouvrir http://192.168.44.191:8899/ dans un navigateur${NC}"
echo ""

# ============================================================
echo -e "${BOLD}${GREEN}"
echo "==============================================================="
echo "   DEMONSTRATION TERMINEE"
echo "   Dashboard Grafana disponible sur : http://192.168.44.191:32201"
echo "==============================================================="
echo -e "${NC}"
