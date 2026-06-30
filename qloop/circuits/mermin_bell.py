"""
Mermin-Bell inequality circuit — standard benchmark (SupermarQ family).

GHZ state preparation followed by measurement in the bases required to
evaluate the Mermin operator. For n=3, the Mermin operator is
M = XXX - XYY - YXY - YYX, with classical (local-hidden-variable) bound
|<M>| <= 2 and quantum (GHZ) value <M> = 4, an exact, analytically known
violation.

Clifford-only: H, CX, and the basis-change S-gates used here are all
Clifford operations, so this routes through the Stim-backed Clifford path.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Statevector

from qloop.core.invariants import hermitian_expectation, normalized
from qloop.core.spec import Budget, CircuitSpec, ParamSpace

_MERMIN_OPERATOR_3 = SparsePauliOp.from_list(
    [("XXX", 1.0), ("XYY", -1.0), ("YXY", -1.0), ("YYX", -1.0)]
)
_EXACT_MERMIN_VALUE = 4.0
_CLASSICAL_BOUND = 2.0


class MerminBellSpec(CircuitSpec):
    """3-qubit GHZ + Mermin operator. Exact quantum violation of the classical bound."""

    name = "mermin-bell"
    n_qubits = 3
    tags = ["clifford", "entanglement", "bell-inequality"]

    def build(self, **params) -> QuantumCircuit:
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.cx(0, 1)
        qc.cx(1, 2)
        return qc

    def reference_state(self, **params) -> Statevector:
        data = np.zeros(8, dtype=complex)
        data[0] = 1.0 / np.sqrt(2)
        data[7] = 1.0 / np.sqrt(2)
        return Statevector(data)

    def reference_expectation(self, **params) -> float:
        return _EXACT_MERMIN_VALUE

    def invariants(self):
        return [
            normalized(),
            hermitian_expectation(_MERMIN_OPERATOR_3, _EXACT_MERMIN_VALUE, atol=1e-9),
        ]

    def budget(self) -> Budget:
        return Budget(depth=10, two_qubit_gates=5, depth_limited=25, two_qubit_gates_limited=10)

    def param_space(self) -> ParamSpace:
        return ParamSpace.empty()

    # No expected_distribution: the Mermin operator's value is what's being
    # tested, not a computational-basis bitstring distribution.


def classical_bound() -> float:
    """Local-hidden-variable bound on |<M>|, exceeded by the GHZ quantum value."""
    return _CLASSICAL_BOUND
