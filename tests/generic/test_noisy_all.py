"""
Generic noisy-simulation tier (Stage 5) — parametrized over registry.all() × noisy targets.

For each (circuit, noisy target) pair:
  - If expected_distribution() is None → skip with a visible reason.
  - Otherwise: sample SHOTS times, assert each outcome's probability is within
    TOLERANCE of the expected value.

GHZ is an example of a circuit that visibly skips this tier (no expected_distribution).
"""

from __future__ import annotations

import pytest
from qiskit import QuantumCircuit

from qloop.backends import noisy_targets
from qloop.backends.noise import build_noise_model, coupling_map_for
from qloop.core.registry import registry
from qloop.pipeline.run import run_sampled
from qloop.pipeline.transpile import transpile_for_target

_ALL = registry.all()
_NOISY = noisy_targets()

SHOTS = 4096
TOLERANCE = 0.07  # allow 7 pp deviation; noise model is approximate

_params = [
    pytest.param(spec, target, id=f"{spec.name}::{target['name']}")
    for spec in _ALL
    for target in _NOISY
]


def _add_measurements(qc: QuantumCircuit) -> QuantumCircuit:
    measured = qc.copy()
    measured.measure_all()
    return measured


@pytest.mark.parametrize("spec,target", _params)
def test_noisy_distribution(spec, target):
    ed = spec.expected_distribution()
    if ed is None:
        pytest.skip(
            f"{spec.name}: no expected_distribution defined — "
            "add def expected_distribution(self) to enable noisy tests"
        )

    noise_model = build_noise_model(target)
    qc = _add_measurements(spec.build())
    coupling_map = coupling_map_for(target, n_qubits=qc.num_qubits)
    transpiled, _ = transpile_for_target(qc, target, coupling_map=coupling_map)

    counts = run_sampled(
        transpiled,
        shots=SHOTS,
        noise_model=noise_model,
        coupling_map=coupling_map,
    )

    for bitstring, expected_prob in ed.items():
        actual_prob = counts.get(bitstring, 0) / SHOTS
        assert abs(actual_prob - expected_prob) <= TOLERANCE, (
            f"{spec.name}@{target['name']}: "
            f"p('{bitstring}') = {actual_prob:.4f}, "
            f"expected {expected_prob:.4f} ± {TOLERANCE}"
        )
