"""
Transpilation matrix tests: every (circuit × target) combination must transpile
successfully and fit within the configured budget.

This is the "build" step — a circuit that exceeds depth or two-qubit gate budget
will cause these tests to fail, just as a compile error blocks a software build.

Budget knob: budgets are defined in backends/targets.yaml under each target's
'budget' key. Tighten them to catch circuits that over-decompose.
"""

from __future__ import annotations

import os

import pytest
import yaml

from backends.noise import coupling_map_for
from circuits.bell import bell_circuit, bell_circuit_measured
from circuits.grover import grover_circuit
from pipeline.transpile import BudgetExceeded, assert_fits, transpile_for_target

_YAML_PATH = os.path.join(os.path.dirname(__file__), "../../backends/targets.yaml")


def _load_targets() -> list[dict]:
    with open(_YAML_PATH) as f:
        data = yaml.safe_load(f)
    return data["targets"]


def _named_circuits() -> list[tuple[str, object]]:
    return [
        ("bell", bell_circuit()),
        ("bell_measured", bell_circuit_measured()),
        ("grover_2q_01", grover_circuit("01")),
        ("grover_2q_10", grover_circuit("10")),
        ("grover_3q_101", grover_circuit("101")),
    ]


TARGETS = _load_targets()
CIRCUITS = _named_circuits()

# Parametrize: (circuit_name, circuit, target)
_params = [
    pytest.param(cname, circ, target, id=f"{cname}::{target['name']}")
    for cname, circ in CIRCUITS
    for target in TARGETS
]


@pytest.mark.parametrize("circuit_name,circuit,target", _params)
def test_transpile_fits_budget(circuit_name, circuit, target, capsys):
    """Transpile each circuit for each target and assert it fits the budget."""
    coupling_map = coupling_map_for(target) if target.get("type") == "noisy" else None

    transpiled, metrics = transpile_for_target(circuit, target, coupling_map=coupling_map)

    # Print metrics for observability (captured by pytest; emitted as CI artifact via -s)
    print(
        f"\n[metrics] {circuit_name} → {target['name']}: "
        f"depth={metrics.depth}, 2q={metrics.two_qubit_gate_count}, "
        f"gates={metrics.gate_counts}"
    )

    assert metrics.mapped_successfully, (
        f"{circuit_name} failed to map to {target['name']}"
    )

    budget = target.get("budget")
    if budget:
        assert_fits(metrics, budget)


@pytest.mark.parametrize("target", TARGETS, ids=[t["name"] for t in TARGETS])
def test_transpile_budget_would_fail_if_exceeded(target):
    """
    Demonstrate that assert_fits raises BudgetExceeded when budget is exceeded.

    This verifies the budget knob actually works — set an impossibly tight budget
    and confirm the assertion fires.
    """
    coupling_map = coupling_map_for(target) if target.get("type") == "noisy" else None
    circuit = grover_circuit("101")  # 3-qubit, relatively deep
    _, metrics = transpile_for_target(circuit, target, coupling_map=coupling_map)

    impossible_budget = {"depth": 0, "two_qubit_gates": 0}
    with pytest.raises(BudgetExceeded):
        assert_fits(metrics, impossible_budget)
