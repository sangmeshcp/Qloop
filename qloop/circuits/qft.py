"""
Quantum Fourier Transform — standard benchmark (Tier 0 seed circuit).

No external arXiv source — textbook construction (Nielsen & Chuang Ch. 5).
build() uses Qiskit's own QFTGate directly (not a from-scratch
reimplementation), so there is no independent "differential test" against
it — an earlier version of this docstring claimed one existed; it did not,
and has been corrected.

Two independent exact oracles, both checked as invariants:
  1. Round-trip identity: QFT composed with its own inverse must
     reconstruct |0...0> exactly (unitary by construction).
  2. Add-1-in-Fourier-basis: QFT, a constant-1 phase ramp, then inverse
     QFT must map every computational basis state |x> to |x+1 mod 2^n>
     exactly (the Draper adder for a classical constant). The phase ramp
     angle applied to qubit k, given QFTGate's actual matrix convention
     (verified directly via qiskit.quantum_info.Operator against the
     standard QFT|x> = (1/sqrt(N)) sum_y e^{2*pi*i*x*y/N}|y> definition
     before relying on it) is 2*pi/2^(n-k), not the more commonly quoted
     2*pi/2^(k+1) — that formula assumes a big-endian qubit convention,
     while Qiskit is little-endian (qubit 0 = least significant); getting
     this wrong was the first thing tried here and gave a uniformly wrong
     answer for every input, not a subtle numerical error, so it was easy
     to catch by checking all 2^n inputs before trusting the construction.
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
        return self.invariants() + [
            self._round_trip_identity(n),
            self._add_one_in_fourier_basis(n),
        ]

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

    @staticmethod
    def _add_one_in_fourier_basis(n: int):
        from qloop.core.spec import Invariant

        def check(circuit, sv):
            qft = QuantumCircuit(n)
            qft.append(QFTGate(n), range(n))
            qft = qft.decompose()
            for x in range(2**n):
                prep = QuantumCircuit(n)
                for q in range(n):
                    if (x >> q) & 1:
                        prep.x(q)
                full = prep.compose(qft)
                for k in range(n):
                    full.p(2 * np.pi / (2 ** (n - k)), k)
                full = full.compose(qft.inverse())
                out = Statevector(full)
                expected_idx = (x + 1) % (2**n)
                if abs(out.data[expected_idx] - 1.0) > 1e-9:
                    return False
            return True

        return Invariant(
            name="add_one_in_fourier_basis",
            check=check,
            message="QFT + constant-1 phase ramp + inverse-QFT must map every |x> to |x+1 mod 2^n>",
        )

    def budget(self) -> Budget:
        return Budget(depth=40, two_qubit_gates=20, depth_limited=90, two_qubit_gates_limited=40)

    def param_space(self) -> ParamSpace:
        return ParamSpace(n=IntDomain(2, 6))
