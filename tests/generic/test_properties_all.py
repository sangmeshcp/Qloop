"""
Generic property-test tier (Stage 3) — parametrized over registry.all().

For each registered circuit:
  - Normalization is always checked (no declaration needed).
  - Additional invariants from invariants_for(**params) are checked.
  - If param_space() is non-empty, Hypothesis sweeps parameter combinations.

Adding a new CircuitSpec automatically participates in all three checks.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from qiskit.quantum_info import Statevector

from qloop.core.registry import registry
from qloop.core.strategies import strategies_for

_ALL = registry.all()


def _run_checks(spec, **params):
    qc = spec.build(**params)
    sv = Statevector(qc)
    for inv in spec.invariants_for(**params):
        assert inv.check(qc, sv), (
            f"{spec.name}[{params}]: invariant '{inv.name}' failed — {inv.message}"
        )


@pytest.mark.parametrize("spec", _ALL, ids=[s.name for s in _ALL])
def test_normalization(spec):
    """State vector probabilities must always sum to 1."""
    qc = spec.build()
    sv = Statevector(qc)
    import numpy as np

    total = float(np.sum(sv.probabilities()))
    assert abs(total - 1.0) < 1e-9, f"{spec.name}: probabilities sum to {total}"


@pytest.mark.parametrize("spec", _ALL, ids=[s.name for s in _ALL])
def test_invariants_default_params(spec):
    """All invariants must hold at default parameters."""
    qc = spec.build()
    sv = Statevector(qc)
    for inv in spec.invariants():
        assert inv.check(qc, sv), (
            f"{spec.name}: invariant '{inv.name}' failed — {inv.message}"
        )


@pytest.mark.parametrize("spec", _ALL, ids=[s.name for s in _ALL])
def test_invariants_param_sweep(spec):
    """Hypothesis sweeps param_space and checks invariants_for across all inputs."""
    ps = spec.param_space()
    if ps.is_empty():
        pytest.skip(f"{spec.name}: no param_space defined; use test_invariants_default_params")

    strats = strategies_for(ps)

    @given(**strats)
    @settings(max_examples=25, deadline=None)
    def _inner(**params):
        _run_checks(spec, **params)

    _inner()
