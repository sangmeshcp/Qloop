"""VQE ansatz circuit plugin."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit

from circuits.vqe import (  # noqa: F401
    HAMILTONIAN,
    ansatz,
    expectation,
    ground_state_energy,
)
from qloop.core.invariants import normalized
from qloop.core.spec import Budget, CircuitSpec


class VQESpec(CircuitSpec):
    """
    2-qubit hardware-efficient VQE ansatz.

    build() returns the ansatz at zero initialisation (not the ground state).
    reference_expectation() is the exact ground-state energy of the toy Hamiltonian
    (used to verify the landscape is accessible, not to compare a single shot).
    """

    name = "vqe"
    n_qubits = 2
    tags = ["variational", "chemistry"]

    def build(self, **params) -> QuantumCircuit:
        return ansatz(np.zeros(4))

    def reference_expectation(self, **params) -> float:
        return ground_state_energy()

    def invariants(self):
        return [normalized()]

    def budget(self) -> Budget:
        return Budget(depth=20, two_qubit_gates=5, depth_limited=20, two_qubit_gates_limited=5)

    # No reference_state: output depends on variational params.
    # No expected_distribution: varies with params; covered in test_properties.
