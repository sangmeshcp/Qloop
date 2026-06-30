"""Grover search circuit plugin."""

from __future__ import annotations

from qiskit import QuantumCircuit

from circuits.grover import grover_circuit  # noqa: F401
from qloop.core.invariants import marked_dominant, normalized
from qloop.core.spec import BitstringDomain, Budget, CircuitSpec, ParamSpace


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
