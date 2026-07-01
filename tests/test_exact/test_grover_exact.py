"""Exact verification of Grover search: marked state must have dominant amplitude."""

import numpy as np
import pytest

from qloop.circuits.grover import grover_circuit
from qloop.pipeline.run import run_ideal


@pytest.mark.parametrize("marked", ["00", "01", "10", "11"])
def test_grover_2qubit_marked_dominant(marked):
    """After one Grover iteration on 2 qubits, the marked state has probability > 0.5."""
    sv = run_ideal(grover_circuit(marked))
    probs = sv.probabilities_dict()
    marked_prob = probs.get(marked, 0.0)
    assert marked_prob > 0.5, (
        f"Marked state '{marked}' probability {marked_prob:.4f} should be dominant (>0.5)"
    )


@pytest.mark.parametrize("marked", ["000", "001", "010", "011", "100", "101", "110", "111"])
def test_grover_3qubit_marked_dominant(marked):
    """After one Grover iteration on 3 qubits, the marked state has higher-than-uniform prob."""
    sv = run_ideal(grover_circuit(marked))
    probs = sv.probabilities_dict()
    marked_prob = probs.get(marked, 0.0)
    uniform = 1.0 / 8.0
    assert marked_prob > uniform, (
        f"Marked state '{marked}' probability {marked_prob:.4f} should exceed uniform {uniform:.4f}"
    )


def test_grover_2qubit_normalization():
    sv = run_ideal(grover_circuit("01"))
    assert abs(np.sum(sv.probabilities()) - 1.0) < 1e-10
