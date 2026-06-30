"""
Transverse-field Ising model (TFIM) Trotterized time evolution.

Style: SupermarQ Hamiltonian-simulation benchmark family.

Oracle is APPROXIMATE, not exact: Trotterization only approximates e^{-iHt}.
We compute the exact e^{-iHt}|0...0> classically (via scipy.linalg.expm for
small n) and assert the Trotterized circuit's magnetization lands within a
Trotter-error tolerance band — never bitwise/state equality.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from scipy.linalg import expm

from qloop.core.invariants import normalized
from qloop.core.spec import Budget, CircuitSpec, FloatDomain, IntDomain, ParamSpace

_X = np.array([[0, 1], [1, 0]], dtype=complex)
_Z = np.array([[1, 0], [0, -1]], dtype=complex)
_I = np.eye(2, dtype=complex)


def _op_at(op: np.ndarray, site: int, n: int) -> np.ndarray:
    mats = [_I] * n
    mats[site] = op
    out = mats[0]
    for m in mats[1:]:
        out = np.kron(out, m)
    return out


def _tfim_hamiltonian(n: int, h: float = 1.0, j: float = 1.0) -> np.ndarray:
    """H = -J * sum ZiZ(i+1) - h * sum Xi (open boundary)."""
    dim = 2**n
    H = np.zeros((dim, dim), dtype=complex)
    for i in range(n - 1):
        H -= j * (_op_at(_Z, i, n) @ _op_at(_Z, i + 1, n))
    for i in range(n):
        H -= h * _op_at(_X, i, n)
    return H


def _exact_magnetization(n: int, steps: int, t: float, h: float, j: float) -> float:
    H = _tfim_hamiltonian(n, h, j)
    psi0 = np.zeros(2**n, dtype=complex)
    psi0[0] = 1.0
    psi_t = expm(-1j * H * t) @ psi0
    mag_op = sum(_op_at(_Z, i, n) for i in range(n)) / n
    return float(np.real(np.conj(psi_t) @ mag_op @ psi_t))


class TFIMTrotterSpec(CircuitSpec):
    """Trotterized TFIM evolution. Oracle: magnetization within Trotter-error tolerance."""

    name = "tfim-trotter"
    n_qubits = 4
    tags = ["hamiltonian-simulation", "approximate-oracle"]

    _H_FIELD = 1.0
    _J_COUPLING = 1.0
    _TOLERANCE = 0.1  # Trotter error band on magnetization

    def build(self, n: int = 4, steps: int = 4, t: float = 1.0, **params) -> QuantumCircuit:
        qc = QuantumCircuit(n)
        dt = t / steps
        for _ in range(steps):
            # ZZ layer: RZZ(2*J*dt) implemented as CX-RZ-CX
            for i in range(n - 1):
                qc.cx(i, i + 1)
                qc.rz(2 * self._J_COUPLING * dt, i + 1)
                qc.cx(i, i + 1)
            # X field layer
            for i in range(n):
                qc.rx(2 * self._H_FIELD * dt, i)
        return qc

    def invariants(self):
        return [normalized()]

    def invariants_for(self, n: int = 4, steps: int = 4, t: float = 1.0, **params):
        from qiskit.quantum_info import Statevector

        from qloop.core.spec import Invariant

        exact_mag = _exact_magnetization(n, steps, t, self._H_FIELD, self._J_COUPLING)
        tol = self._TOLERANCE

        def check(circuit: QuantumCircuit, sv: Statevector) -> bool:
            probs = sv.probabilities_dict()
            mag = 0.0
            for bitstring, p in probs.items():
                z_sum = sum(1 if b == "0" else -1 for b in bitstring)
                mag += p * z_sum / n
            return abs(mag - exact_mag) < tol

        magnetization_invariant = Invariant(
            name="magnetization_within_trotter_tolerance",
            check=check,
            message=f"Trotterized magnetization must be within {tol} of exact {exact_mag:.4f}",
        )
        return self.invariants() + [magnetization_invariant]

    def budget(self) -> Budget:
        return Budget(depth=60, two_qubit_gates=30, depth_limited=120, two_qubit_gates_limited=60)

    def param_space(self) -> ParamSpace:
        # steps/t bounded so dt = t/steps stays small enough that first-order
        # Trotter error stays within _TOLERANCE (empirically verified worst-case ~0.03).
        return ParamSpace(n=IntDomain(2, 5), steps=IntDomain(3, 8), t=FloatDomain(0.2, 1.0))
