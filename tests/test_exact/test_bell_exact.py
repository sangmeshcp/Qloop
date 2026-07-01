"""Exact verification of Bell state against known statevector."""

import numpy as np

from qloop.circuits.bell import bell_circuit
from qloop.pipeline.run import run_ideal

INV_SQRT2 = 1.0 / np.sqrt(2)
# |Φ+⟩ = (|00⟩ + |11⟩)/√2 in computational basis ordering [00, 01, 10, 11]
BELL_STATEVECTOR = np.array([INV_SQRT2, 0.0, 0.0, INV_SQRT2], dtype=complex)


def test_bell_statevector():
    sv = run_ideal(bell_circuit())
    np.testing.assert_allclose(sv.data, BELL_STATEVECTOR, atol=1e-10)


def test_bell_probabilities():
    sv = run_ideal(bell_circuit())
    probs = sv.probabilities()
    # Only |00⟩ and |11⟩ should have non-zero probability
    np.testing.assert_allclose(probs[0], 0.5, atol=1e-10)  # |00⟩
    np.testing.assert_allclose(probs[1], 0.0, atol=1e-10)  # |01⟩
    np.testing.assert_allclose(probs[2], 0.0, atol=1e-10)  # |10⟩
    np.testing.assert_allclose(probs[3], 0.5, atol=1e-10)  # |11⟩


def test_bell_normalization():
    sv = run_ideal(bell_circuit())
    assert abs(np.sum(sv.probabilities()) - 1.0) < 1e-10
