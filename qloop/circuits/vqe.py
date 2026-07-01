"""
VQE ansatz circuit plugin.

Toy Hamiltonian: H = -0.5*ZZ - 0.5*XX + 0.2*ZI. Ground-state energy ≈ -1.04
(verified via exact diagonalization in ground_state_energy()).
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Statevector

from qloop.core.invariants import normalized
from qloop.core.spec import Budget, CircuitSpec

HAMILTONIAN = SparsePauliOp.from_list([("ZZ", -0.5), ("XX", -0.5), ("ZI", 0.2)])


def ansatz(params: list[float] | np.ndarray) -> QuantumCircuit:
    """
    Hardware-efficient 2-qubit ansatz with 4 parameters.

    Layer: Ry(θ0)⊗Ry(θ1) → CX → Ry(θ2)⊗Ry(θ3)
    """
    if len(params) != 4:
        raise ValueError(f"ansatz requires 4 parameters, got {len(params)}")
    qc = QuantumCircuit(2)
    qc.ry(params[0], 0)
    qc.ry(params[1], 1)
    qc.cx(0, 1)
    qc.ry(params[2], 0)
    qc.ry(params[3], 1)
    return qc


def expectation(params: list[float] | np.ndarray) -> float:
    """Compute ⟨ψ(params)|H|ψ(params)⟩ via statevector."""
    sv = Statevector(ansatz(params))
    return float(sv.expectation_value(HAMILTONIAN).real)


def ground_state_energy() -> float:
    """
    Compute exact ground-state energy of HAMILTONIAN for test reference.

    Returns the minimum eigenvalue of the 4×4 Hermitian matrix.
    """
    matrix = HAMILTONIAN.to_matrix()
    eigenvalues = np.linalg.eigvalsh(matrix)
    return float(eigenvalues[0])


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
