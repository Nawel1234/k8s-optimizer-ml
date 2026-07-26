"""
Module de collecte des metriques Kubernetes depuis Prometheus.
"""

import requests
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import PROMETHEUS_URL


class PrometheusCollector:

    def __init__(self, base_url: str = PROMETHEUS_URL):
        self.base_url = base_url

    def _query(self, promql: str) -> dict:
        resp = requests.get(
            f"{self.base_url}/api/v1/query",
            params={"query": promql},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def _query_range(self, promql: str, start: datetime, end: datetime, step: str = "30s") -> dict:
        resp = requests.get(
            f"{self.base_url}/api/v1/query_range",
            params={
                "query": promql,
                "start": start.timestamp(),
                "end": end.timestamp(),
                "step": step,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def get_current_usage(self, pod: str, namespace: str) -> dict:
        cpu_query = (
            f'sum(rate(container_cpu_usage_seconds_total{{pod="{pod}", '
            f'namespace="{namespace}", container!=""}}[2m]))'
        )
        mem_query = (
            f'sum(container_memory_working_set_bytes{{pod="{pod}", '
            f'namespace="{namespace}", container!=""}})'
        )
        cpu_result = self._query(cpu_query)
        mem_result = self._query(mem_query)
        cpu_val = self._extract_scalar(cpu_result)
        mem_val = self._extract_scalar(mem_result)
        return {"cpu_cores": cpu_val, "mem_bytes": mem_val}

    def get_recent_history(self, pod: str, namespace: str, points: int = 5, step_seconds: int = 30) -> dict:
        """
        Recupere les N dernieres valeurs reelles (pas juste l'instant present)
        pour construire de vrais lags/rolling stats, comme pendant l'entrainement.
        """
        end = datetime.utcnow()
        start = end - timedelta(seconds=points * step_seconds * 3)

        cpu_query = (
            f'sum(rate(container_cpu_usage_seconds_total{{pod="{pod}", '
            f'namespace="{namespace}", container!=""}}[2m]))'
        )
        mem_query = (
            f'sum(container_memory_working_set_bytes{{pod="{pod}", '
            f'namespace="{namespace}", container!=""}})'
        )

        cpu_data = self._query_range(cpu_query, start, end, step=f"{step_seconds}s")
        mem_data = self._query_range(mem_query, start, end, step=f"{step_seconds}s")

        def extract_values(result):
            data = result.get("data", {}).get("result", [])
            if not data:
                return []
            return [float(v) for _, v in data[0]["values"]]

        cpu_values = extract_values(cpu_data)
        mem_values = extract_values(mem_data)

        if not cpu_values or not mem_values:
            current = self.get_current_usage(pod, namespace)
            if not cpu_values:
                cpu_values = [current["cpu_cores"]]
            if not mem_values:
                mem_values = [current["mem_bytes"]]

        cpu_values = cpu_values[-points:] if cpu_values else [0.0]
        mem_values = mem_values[-points:] if mem_values else [0.0]

        return {"cpu_history": cpu_values, "mem_history": mem_values}

    @staticmethod
    def _extract_scalar(result: dict):
        data = result.get("data", {}).get("result", [])
        if not data:
            return 0.0
        return float(data[0]["value"][1])


if __name__ == "__main__":
    collector = PrometheusCollector()
    print(f"Test connexion a {PROMETHEUS_URL} ...")
    result = collector._query("up")
    print(f"Reponse: {len(result.get('data', {}).get('result', []))} targets actifs")

    print("\nTest get_recent_history sur prometheus-server...")
    hist = collector.get_recent_history("prometheus-server-56bc86bdd7-swdh6", "monitoring", points=5)
    print(f"CPU history: {hist['cpu_history']}")
    print(f"MEM history: {hist['mem_history']}")
