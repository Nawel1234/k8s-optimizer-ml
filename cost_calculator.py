"""
Module de traduction des gains de ressources en valeur economique.

Utilise des tarifs cloud publics indicatifs (references : AWS EC2 On-Demand,
instances polyvalentes de la famille M, region eu-west) pour convertir les
economies de CPU/RAM en estimation de cout mensuel/annuel.

Ces tarifs sont indicatifs et doivent etre ajustes selon le fournisseur
cloud reellement vise en production (AWS, Azure, GCP, ou infrastructure
on-premise avec cout d'amortissement materiel).
"""

# Tarifs indicatifs (USD), a adapter selon le contexte reel
PRIX_VCPU_HEURE = 0.0416    # USD par vCPU/heure (reference AWS m5.large ~2024)
PRIX_GB_RAM_HEURE = 0.0053  # USD par Go de RAM/heure
HEURES_PAR_MOIS = 730       # moyenne (24h x 30.4 jours)


def calculer_economie(cpu_avant_millicores, cpu_apres_millicores,
                       ram_avant_mb, ram_apres_mb):
    """
    Calcule l'economie mensuelle et annuelle estimee suite a l'optimisation.
    Une valeur negative signifie un surcout (cas d'un scale-up justifie
    par une charge reelle plus elevee que prevu).
    """
    gain_cpu_vcpu = (cpu_avant_millicores - cpu_apres_millicores) / 1000
    gain_ram_gb = (ram_avant_mb - ram_apres_mb) / 1024

    economie_horaire = (gain_cpu_vcpu * PRIX_VCPU_HEURE +
                         gain_ram_gb * PRIX_GB_RAM_HEURE)
    economie_mensuelle = economie_horaire * HEURES_PAR_MOIS
    economie_annuelle = economie_mensuelle * 12

    return {
        "economie_mensuelle_usd": round(economie_mensuelle, 2),
        "economie_annuelle_usd": round(economie_annuelle, 2),
        "gain_cpu_vcpu": round(gain_cpu_vcpu, 4),
        "gain_ram_gb": round(gain_ram_gb, 4),
    }


if __name__ == "__main__":
    # Exemple avec les valeurs reelles observees sur nginx-test
    resultat = calculer_economie(
        cpu_avant_millicores=500, cpu_apres_millicores=6,
        ram_avant_mb=512, ram_apres_mb=12
    )
    print("Exemple - nginx-test :")
    for k, v in resultat.items():
        print(f"  {k}: {v}")
