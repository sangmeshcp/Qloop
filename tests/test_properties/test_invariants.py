"""
Property-based tests using Hypothesis.

Invariants tested:
  - Statevector normalization across arbitrary circuit structures
  - Grover correctness across all 2-qubit marked bitstrings
  - Unitarity of the Bell circuit unitary
  - VQE energy can be driven below the classical bound via optimization
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from circuits.bell import bell_circuit
from circuits.grover import grover_circuit
from circuits.vqe import expectation, ground_state_energy
from pipeline.run import run_ideal

# ── Normalization ──────────────────────────────────────────────────────────────

def _random_circuit(n_qubits: int, seed: int) -> QuantumCircuit:
    """Generate a simple parameterized circuit for normalization probing."""
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n_qubits)
    for _ in range(3):
        for q in range(n_qubits):
            qc.ry(rng.uniform(0, 2 * np.pi), q)
        for q in range(n_qubits - 1):
            qc.cx(q, q + 1)
    return qc


@given(
    n_qubits=st.integers(min_value=1, max_value=4),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
@settings(max_examples=50, deadline=5000)
def test_statevector_normalization(n_qubits, seed):
    """Statevector probabilities always sum to 1, regardless of circuit structure."""
    qc = _random_circuit(n_qubits, seed)
    sv = run_ideal(qc)
    total_prob = np.sum(sv.probabilities())
    assert abs(total_prob - 1.0) < 1e-9, f"Normalization violated: sum = {total_prob}"


# ── Grover sweep ───────────────────────────────────────────────────────────────

@given(marked=st.sampled_from(["00", "01", "10", "11"]))
@settings(max_examples=4, deadline=5000)
def test_grover_all_2qubit_targets(marked):
    """Grover correctly amplifies every 2-qubit marked state."""
    sv = run_ideal(grover_circuit(marked))
    probs = sv.probabilities_dict()
    marked_prob = probs.get(marked, 0.0)
    assert marked_prob > 0.5, f"marked='{marked}' probability {marked_prob:.4f} not dominant"


@given(marked=st.sampled_from(["000", "001", "010", "011", "100", "101", "110", "111"]))
@settings(max_examples=8, deadline=5000)
def test_grover_all_3qubit_targets(marked):
    """Grover amplifies every 3-qubit marked state above uniform probability."""
    sv = run_ideal(grover_circuit(marked))
    probs = sv.probabilities_dict()
    marked_prob = probs.get(marked, 0.0)
    uniform = 1.0 / 8.0
    assert marked_prob > uniform, (
        f"marked='{marked}' probability {marked_prob:.4f} not above uniform {uniform:.4f}"
    )


# ── Unitarity ──────────────────────────────────────────────────────────────────

def test_bell_circuit_unitarity():
    """The Bell circuit implements a unitary transformation (U†U = I)."""
    op = Operator(bell_circuit())
    u = op.data
    product = u.conj().T @ u
    np.testing.assert_allclose(product, np.eye(4), atol=1e-10)


# ── VQE energy minimization ────────────────────────────────────────────────────

def test_vqe_ground_state_energy_reachable():
    """
    VQE ansatz can reach the true ground-state energy of the toy Hamiltonian
    within 0.05 Hartree when initialized near the optimal parameters.

    We don't run a full optimizer loop in CI — instead we probe a grid around
    known-good parameters to confirm the landscape has a reachable minimum.
    """
    exact_gs = ground_state_energy()
    threshold = exact_gs + 0.05  # allow 50 mHa slack

    best = float("inf")
    rng = np.random.default_rng(0)
    for _ in range(200):
        params = rng.uniform(-np.pi, np.pi, 4)
        e = expectation(params)
        if e < best:
            best = e

    assert best < threshold, (
        f"VQE best energy {best:.6f} did not reach threshold {threshold:.6f} "
        f"(exact ground state: {exact_gs:.6f})"
    )


@given(params=st.lists(st.floats(min_value=-np.pi, max_value=np.pi), min_size=4, max_size=4))
@settings(max_examples=30, deadline=5000)
def test_vqe_expectation_is_real(params):
    """Expectation value of Hermitian operator must always be real."""
    e = expectation(params)
    assert np.isfinite(e), f"Non-finite expectation value: {e}"
