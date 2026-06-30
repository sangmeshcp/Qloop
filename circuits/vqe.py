"""
Minimal VQE for a 2-qubit toy Hamiltonian.

Hamiltonian: H = -0.5 * ZZ - 0.5 * XX + 0.2 * ZI
Ground truth ground-state energy ≈ -1.0 (verified analytically).
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Statevector


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


# Toy Hamiltonian: H = -0.5*ZZ - 0.5*XX + 0.2*ZI
HAMILTONIAN = SparsePauliOp.from_list([("ZZ", -0.5), ("XX", -0.5), ("ZI", 0.2)])


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
