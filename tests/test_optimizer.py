import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimizer.controller import (
    parse_cpu_to_cores,
    parse_mem_to_bytes,
    cores_to_cpu_str,
    bytes_to_mem_str,
    calculate_target_replicas,
)


def test_parse_cpu_to_cores_millicores():
    assert parse_cpu_to_cores("500m") == 0.5

def test_parse_mem_to_bytes_mebibytes():
    assert parse_mem_to_bytes("256Mi") == 256 * 1024 * 1024

def test_cores_to_cpu_str():
    assert cores_to_cpu_str(0.5) == "500m"

def test_bytes_to_mem_str():
    assert bytes_to_mem_str(256 * 1024 * 1024) == "256Mi"

def test_calculate_target_replicas_scale_up():
    result = calculate_target_replicas(current_replicas=1, predicted_cpu=0.45, current_cpu_request=0.5)
    assert result == 2

def test_calculate_target_replicas_scale_down():
    result = calculate_target_replicas(current_replicas=2, predicted_cpu=0.05, current_cpu_request=0.5)
    assert result == 1
