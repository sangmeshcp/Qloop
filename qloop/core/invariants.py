"""
Reusable Invariant library.

Each factory function returns an Invariant(name, check, message).
These are composed in CircuitSpec.invariants() / invariants_for().
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector

from qloop.core.spec import Invariant


def normalized(atol: float = 1e-9) -> Invariant:
    """Statevector probabilities sum to 1."""

    def check(circuit: QuantumCircuit, sv: Statevector) -> bool:
        return abs(np.sum(sv.probabilities()) - 1.0) < atol

    return Invariant(
        name="normalized",
        check=check,
        message=f"Probabilities must sum to 1 (atol={atol})",
    )


def unitary(atol: float = 1e-9) -> Invariant:
    """Circuit implements a unitary transformation (U†U = I)."""

    def check(circuit: QuantumCircuit, sv: Statevector) -> bool:
        u = Operator(circuit).data
        return np.allclose(u.conj().T @ u, np.eye(len(u)), atol=atol)

    return Invariant(
        name="unitary",
        check=check,
        message="U†U must equal identity",
    )


def marked_dominant(marked: str, threshold: float = 0.5) -> Invariant:
    """Marked state has probability above threshold (for 2-qubit Grover)."""

    def check(circuit: QuantumCircuit, sv: Statevector) -> bool:
        return sv.probabilities_dict().get(marked, 0.0) > threshold

    return Invariant(
        name=f"marked_dominant[{marked}]",
        check=check,
        message=f"p('{marked}') must exceed {threshold}",
    )


def above_uniform(n_qubits: int, marked: str) -> Invariant:
    """Marked state has probability above the uniform baseline 1/2^n."""
    uniform = 1.0 / (2**n_qubits)

    def check(circuit: QuantumCircuit, sv: Statevector) -> bool:
        return sv.probabilities_dict().get(marked, 0.0) > uniform

    return Invariant(
        name=f"above_uniform[{marked}]",
        check=check,
        message=f"p('{marked}') must exceed uniform {uniform:.4f}",
    )


def hamming_weight_exact(k: int, atol: float = 1e-9) -> Invariant:
    """Every basis state with non-negligible amplitude has exactly k ones."""

    def check(circuit: QuantumCircuit, sv: Statevector) -> bool:
        for idx, prob in enumerate(sv.probabilities()):
            if prob > atol:
                weight = bin(idx).count("1")
                if weight != k:
                    return False
        return True

    return Invariant(
        name=f"hamming_weight_exact[{k}]",
        check=check,
        message=f"All non-negligible-amplitude basis states must have Hamming weight {k}",
    )


def real_nonnegative_amplitudes(atol: float = 1e-9) -> Invariant:
    """Every amplitude is real and non-negative (no complex phase)."""

    def check(circuit: QuantumCircuit, sv: Statevector) -> bool:
        return bool(np.all(np.abs(sv.data.imag) < atol) and np.all(sv.data.real > -atol))

    return Invariant(
        name="real_nonnegative_amplitudes",
        check=check,
        message="All amplitudes must be real and non-negative",
    )


def heavy_output_probability_exceeds(threshold: float = 2.0 / 3.0) -> Invariant:
    """
    Aggregate probability of 'heavy' outcomes (those above the median
    probability across all computational basis states) exceeds threshold.

    This is the Quantum Volume success criterion (Cross et al.): a Haar-
    random circuit's ideal output distribution should concentrate more than
    2/3 of its probability mass on the above-median ("heavy") outcomes.
    """

    def check(circuit: QuantumCircuit, sv: Statevector) -> bool:
        probs = sv.probabilities()
        median = np.median(probs)
        heavy_probability = float(np.sum(probs[probs > median]))
        return heavy_probability > threshold

    return Invariant(
        name=f"heavy_output_probability_exceeds[{threshold:.3f}]",
        check=check,
        message=f"Heavy-output probability must exceed {threshold:.3f}",
    )


def zz_expectation_equals(i: int, j: int, expected: float = 1.0, atol: float = 1e-9) -> Invariant:
    """<Z_i Z_j> equals expected (e.g. +1 for any pair on a GHZ state)."""

    def check(circuit: QuantumCircuit, sv: Statevector) -> bool:
        n = circuit.num_qubits
        label = ["I"] * n
        label[n - 1 - i] = "Z"
        label[n - 1 - j] = "Z"
        from qiskit.quantum_info import SparsePauliOp

        op = SparsePauliOp("".join(label))
        val = float(sv.expectation_value(op).real)
        return abs(val - expected) < atol

    return Invariant(
        name=f"zz_expectation[{i},{j}]",
        check=check,
        message=f"<Z_{i} Z_{j}> must equal {expected}",
    )


def hermitian_expectation(observable, expected: float, atol: float = 0.1) -> Invariant:
    """⟨ψ|H|ψ⟩ is within atol of expected (for variational circuits)."""

    def check(circuit: QuantumCircuit, sv: Statevector) -> bool:
        val = float(sv.expectation_value(observable).real)
        return abs(val - expected) < atol

    return Invariant(
        name="hermitian_expectation",
        check=check,
        message=f"⟨H⟩ must be within {atol} of {expected}",
    )
