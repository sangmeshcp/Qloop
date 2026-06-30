"""
Generic Clifford/Stim property tier — parametrized over registry.all().

For each registered circuit:
  - If stim_program() returns None → skip with a visible reason (the default
    for every non-Clifford or small circuit; this tier is additive, not a
    replacement for the statevector-based property tier).
  - Otherwise: sweep stim_param_space() (independent from param_space(), which
    drives the statevector sweep) and assert each compiled detector circuit's
    detectors are quiescent absent an injected error, and fire when one is
    injected (error_qubit >= 0 by convention).

This is the only property-verification path exercised for circuits too large
for statevector simulation (n_qubits > MAX_STATEVECTOR_QUBITS) — e.g. the
bivariate-bicycle QEC syndrome-extraction circuits.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings

from qloop.core.registry import registry
from qloop.core.strategies import strategies_for

_ALL = registry.all()


def _assert_detector_behavior(spec, prog, params):
    sampler = prog.compile_detector_sampler()
    detectors = sampler.sample(shots=4)
    error_injected = params.get("error_qubit", -1) >= 0
    if error_injected:
        assert detectors.any(), (
            f"{spec.name}{params}: expected at least one detector to fire "
            "after error injection"
        )
    else:
        assert not detectors.any(), (
            f"{spec.name}{params}: detectors must be quiescent absent errors "
            "(syndrome-extraction circuit is not reproducible round-to-round)"
        )


@pytest.mark.parametrize("spec", _ALL, ids=[s.name for s in _ALL])
def test_stim_program(spec):
    ps = spec.stim_param_space()

    if ps.is_empty():
        prog = spec.stim_program()
        if prog is None:
            pytest.skip(f"{spec.name}: no stim_program defined")
        _assert_detector_behavior(spec, prog, {})
        return

    strats = strategies_for(ps)

    @given(**strats)
    @settings(max_examples=20, deadline=None)
    def _inner(**params):
        prog = spec.stim_program(**params)
        if prog is None:
            return
        _assert_detector_behavior(spec, prog, params)

    _inner()
