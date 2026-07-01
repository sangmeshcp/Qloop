"""Grover search circuit plugin."""

from __future__ import annotations

from qiskit import QuantumCircuit

from qloop.core.invariants import marked_dominant, normalized
from qloop.core.spec import BitstringDomain, Budget, CircuitSpec, ParamSpace


def _oracle(qc: QuantumCircuit, marked: str) -> None:
    """Phase-flip oracle: flips sign of |marked⟩."""
    n = len(marked)
    # Flip qubits where the marked bit is '0' (LSB = qubit 0)
    for i, bit in enumerate(reversed(marked)):
        if bit == "0":
            qc.x(i)
    # Multi-controlled Z via CX + H trick
    if n == 2:
        qc.h(1)
        qc.cx(0, 1)
        qc.h(1)
    elif n == 3:
        qc.h(2)
        qc.ccx(0, 1, 2)
        qc.h(2)
    # Unflip
    for i, bit in enumerate(reversed(marked)):
        if bit == "0":
            qc.x(i)


def _diffuser(qc: QuantumCircuit, n: int) -> None:
    """Grover diffusion operator (inversion about average)."""
    qc.h(range(n))
    qc.x(range(n))
    if n == 2:
        qc.h(1)
        qc.cx(0, 1)
        qc.h(1)
    elif n == 3:
        qc.h(2)
        qc.ccx(0, 1, 2)
        qc.h(2)
    qc.x(range(n))
    qc.h(range(n))


def grover_circuit(marked: str) -> QuantumCircuit:
    """
    Grover search circuit for a 2- or 3-qubit marked bitstring.

    Args:
        marked: Target bitstring, e.g. '10' or '101'. Length determines qubit count.

    Returns:
        QuantumCircuit with one Grover iteration (no measurement).
    """
    n = len(marked)
    if n not in (2, 3):
        raise ValueError(f"marked must be 2 or 3 bits, got {n}")

    qc = QuantumCircuit(n)
    qc.h(range(n))        # uniform superposition
    _oracle(qc, marked)   # phase kick
    _diffuser(qc, n)      # amplitude amplification
    return qc


class GroverSpec(CircuitSpec):
    """
    2-qubit Grover search.  param_space sweeps all 2-bit marked strings.
    For 3-qubit Grover, the existing test_exact/test_grover_exact.py covers it;
    a separate Grover3Spec can be added as a single-file extension.
    """

    name = "grover"
    n_qubits = 2
    tags = ["search", "amplitude-amplification"]

    def build(self, marked: str = "01", **params) -> QuantumCircuit:
        return grover_circuit(marked)

    # No reference_state: the amplified superposition is non-trivial analytically;
    # the marked_dominant invariant captures correctness without a closed form.

    def invariants_for(self, marked: str = "01", **params):
        return [normalized(), marked_dominant(marked, threshold=0.5)]

    def budget(self) -> Budget:
        return Budget(
            depth=30,
            two_qubit_gates=10,
            depth_limited=30,
            two_qubit_gates_limited=10,
        )

    def param_space(self) -> ParamSpace:
        return ParamSpace(marked=BitstringDomain(length=2))

    # No expected_distribution: Grover output is a superposition not easily
    # characterised by a few dominant bitstrings after noise.
