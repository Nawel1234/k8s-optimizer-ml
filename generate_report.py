"""
Genere un rapport professionnel avant/apres a partir des logs
de l'Optimizer Controller (optimizer_actions.log).
"""
import json
import os
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "optimizer_actions.log")


def parse_cpu_to_millicores(cpu_str):
    """Convertit '500m' -> 500, '1' -> 1000"""
    if cpu_str.endswith("m"):
        return int(cpu_str[:-1])
    return int(float(cpu_str) * 1000)


def parse_mem_to_mb(mem_str):
    """Convertit '512Mi' -> 512, '1Gi' -> 1024"""
    if mem_str.endswith("Mi"):
        return int(mem_str[:-2])
    if mem_str.endswith("Gi"):
        return int(float(mem_str[:-2]) * 1024)
    return int(mem_str)


def load_actions():
    actions = []
    if not os.path.exists(LOG_PATH):
        print(f"Aucun log trouve a {LOG_PATH}")
        return actions
    with open(LOG_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                actions.append(json.loads(line))
    return actions


def print_report(actions):
    print("=" * 100)
    print(" " * 25 + "RAPPORT D'OPTIMISATION - KUBERNETES INTELLIGENT RESOURCE OPTIMIZER")
    print("=" * 100)
    print(f"Date de generation : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Nombre d'actions d'optimisation enregistrees : {len(actions)}")
    print("=" * 100)
    print()

    total_cpu_before = 0
    total_cpu_after = 0
    total_mem_before = 0
    total_mem_after = 0

    header = f"{'Deployment':<20} {'CPU Avant':<12} {'CPU Apres':<12} {'Gain CPU':<10} {'RAM Avant':<12} {'RAM Apres':<12} {'Gain RAM':<10}"
    print(header)
    print("-" * len(header))

    for action in actions:
        dep = action["deployment"]
        cpu_before_m = parse_cpu_to_millicores(action["before"]["cpu_request"])
        cpu_after_m = parse_cpu_to_millicores(action["after"]["cpu_request"])
        mem_before_mb = parse_mem_to_mb(action["before"]["mem_request"])
        mem_after_mb = parse_mem_to_mb(action["after"]["mem_request"])

        cpu_gain = (1 - cpu_after_m / cpu_before_m) * 100 if cpu_before_m > 0 else 0
        mem_gain = (1 - mem_after_mb / mem_before_mb) * 100 if mem_before_mb > 0 else 0

        total_cpu_before += cpu_before_m
        total_cpu_after += cpu_after_m
        total_mem_before += mem_before_mb
        total_mem_after += mem_after_mb

        print(f"{dep:<20} {str(cpu_before_m)+'m':<12} {str(cpu_after_m)+'m':<12} "
              f"{'-'+str(round(cpu_gain,1))+'%':<10} {str(mem_before_mb)+'Mi':<12} "
              f"{str(mem_after_mb)+'Mi':<12} {'-'+str(round(mem_gain,1))+'%':<10}")

    print("-" * len(header))

    total_cpu_gain = (1 - total_cpu_after / total_cpu_before) * 100 if total_cpu_before > 0 else 0
    total_mem_gain = (1 - total_mem_after / total_mem_before) * 100 if total_mem_before > 0 else 0

    print(f"\n{'TOTAL':<20} {str(total_cpu_before)+'m':<12} {str(total_cpu_after)+'m':<12} "
          f"{'-'+str(round(total_cpu_gain,1))+'%':<10} {str(total_mem_before)+'Mi':<12} "
          f"{str(total_mem_after)+'Mi':<12} {'-'+str(round(total_mem_gain,1))+'%':<10}")

    print()
    print("=" * 100)
    print("SYNTHESE")
    print("=" * 100)
    print(f"Reduction totale CPU alloue    : {total_cpu_gain:.1f}%  ({total_cpu_before}m -> {total_cpu_after}m)")
    print(f"Reduction totale RAM allouee   : {total_mem_gain:.1f}%  ({total_mem_before}Mi -> {total_mem_after}Mi)")
    print(f"Nombre de deployments optimises : {len(actions)}")
    print("=" * 100)

    # Export CSV pour le rapport
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rapport_optimisation.csv")
    with open(csv_path, "w") as f:
        f.write("Deployment,CPU_Avant_m,CPU_Apres_m,Gain_CPU_pct,RAM_Avant_Mi,RAM_Apres_Mi,Gain_RAM_pct\n")
        for action in actions:
            dep = action["deployment"]
            cpu_before_m = parse_cpu_to_millicores(action["before"]["cpu_request"])
            cpu_after_m = parse_cpu_to_millicores(action["after"]["cpu_request"])
            mem_before_mb = parse_mem_to_mb(action["before"]["mem_request"])
            mem_after_mb = parse_mem_to_mb(action["after"]["mem_request"])
            cpu_gain = (1 - cpu_after_m / cpu_before_m) * 100 if cpu_before_m > 0 else 0
            mem_gain = (1 - mem_after_mb / mem_before_mb) * 100 if mem_before_mb > 0 else 0
            f.write(f"{dep},{cpu_before_m},{cpu_after_m},{cpu_gain:.1f},{mem_before_mb},{mem_after_mb},{mem_gain:.1f}\n")

    print(f"\nRapport CSV exporte : {csv_path}")


if __name__ == "__main__":
    actions = load_actions()
    if actions:
        print_report(actions)
    else:
        print("Aucune action d'optimisation trouvee. Lance d'abord optimizer/controller.py")
