"""
Generic transpile tier (Stage 4) — parametrized over registry.all() × all targets.

For each (circuit, target) pair:
  - Transpile to target's native gate set and topology.
  - Assert depth and two-qubit gate count fit spec.budget().for_target(target).
  - Record metrics via qloop.pipeline.report.

Adding a new CircuitSpec or target automatically joins the matrix.
"""

from __future__ import annotations

import pytest

from backends.noise import coupling_map_for
from pipeline.transpile import assert_fits, transpile_for_target
from qloop.backends import load_targets
from qloop.core.registry import registry
from qloop.pipeline.report import metrics

_ALL = registry.all()
_TARGETS = load_targets()

_params = [
    pytest.param(spec, target, id=f"{spec.name}::{target['name']}")
    for spec in _ALL
    for target in _TARGETS
]


@pytest.mark.parametrize("spec,target", _params)
def test_transpile_fits_budget(spec, target, capsys):
    qc = spec.build()
    coupling_map = (
        coupling_map_for(target, n_qubits=qc.num_qubits) if target.get("type") == "noisy" else None
    )

    transpiled, m = transpile_for_target(qc, target, coupling_map=coupling_map)

    metrics.record(
        spec.name,
        target["name"],
        "transpile",
        depth=m.depth,
        two_qubit_gates=m.two_qubit_gate_count,
        mapped=m.mapped_successfully,
    )

    print(
        f"\n[metrics] {spec.name} → {target['name']}: "
        f"depth={m.depth}, 2q={m.two_qubit_gate_count}, "
        f"gates={m.gate_counts}"
    )

    assert m.mapped_successfully, (
        f"{spec.name} failed to map to {target['name']}"
    )

    budget = spec.budget().for_target(target)
    assert_fits(m, budget)
