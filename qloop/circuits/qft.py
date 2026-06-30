"""
Quantum Fourier Transform — standard benchmark (Tier 0 seed circuit).

Exact oracle via round-trip identity: QFT followed by inverse-QFT must
reconstruct the input exactly (up to global phase), since QFT is unitary
and its inverse is its conjugate transpose by construction.

No external arXiv source — textbook construction (Nielsen & Chuang Ch. 5).
Differential-tested against qiskit.circuit.library.QFT.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFTGate
from qiskit.quantum_info import Statevector

from qloop.core.invariants import normalized, unitary
from qloop.core.spec import Budget, CircuitSpec, IntDomain, ParamSpace


class QFTSpec(CircuitSpec):
    """QFT on n qubits, starting from |0...0> so the oracle is trivially the same state."""

    name = "qft"
    n_qubits = 4
    tags = ["fourier", "topology-sensitive"]

    def build(self, n: int = 4, **params) -> QuantumCircuit:
        qc = QuantumCircuit(n)
        qc.append(QFTGate(n), range(n))
        return qc.decompose()

    def reference_state(self, n: int = 4, **params) -> Statevector:
        # QFT|0...0> = uniform superposition over all computational basis states.
        dim = 2**n
        return Statevector(np.full(dim, 1.0 / np.sqrt(dim), dtype=complex))

    def invariants(self):
        return [normalized(), unitary()]

    def invariants_for(self, n: int = 4, **params):
        return self.invariants() + [self._round_trip_identity(n)]

    @staticmethod
    def _round_trip_identity(n: int):
        from qloop.core.spec import Invariant

        def check(circuit, sv):
            qft = QuantumCircuit(n)
            qft.append(QFTGate(n), range(n))
            qft = qft.decompose()
            round_trip = qft.compose(qft.inverse())
            ident = Statevector.from_label("0" * n).evolve(round_trip)
            ref = Statevector.from_label("0" * n)
            return np.allclose(ident.data, ref.data, atol=1e-9)

        return Invariant(
            name="qft_round_trip_identity",
            check=check,
            message="QFT composed with its inverse must reconstruct |0...0>",
        )

    def budget(self) -> Budget:
        return Budget(depth=40, two_qubit_gates=20, depth_limited=90, two_qubit_gates_limited=40)

    def param_space(self) -> ParamSpace:
        return ParamSpace(n=IntDomain(2, 6))
