"""
GHZ state circuit plugin — the framework's original proof-of-concept.

This file is the ONLY thing needed to add a new circuit to the full pipeline.
After dropping it in qloop/circuits/, pytest automatically:
  v exact-tests it (reference_state is defined)
  v checks normalization, unitarity, and Z-parity stabilizers (invariants)
  v transpiles it across all three targets (budget defined)
  x skips the noisy tier with a visible reason (no expected_distribution)

CNOT-ladder construction: H on qubit 0, then CX(i, i+1) for i=0..n-2 —
depth O(n). Paired with ghz_tree.py (same oracle, log-depth O(log n)
CNOT-tree construction) at the same default qubit count (12) for an
explicit topology-sensitivity contrast.

Measured result (not the naively expected one — see ghz_tree.py's
docstring for the full explanation): the ladder is already nearest-
neighbor-local, so it costs LESS on heavy-hex than the logically-shallower
tree, whose long-range CNOTs need SWAP routing that a linear structure
doesn't. Logical depth and post-transpile cost are not the same thing,
which is the transpile-matrix stage's entire reason for existing.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qloop.core.invariants import normalized, unitary, zz_expectation_equals
from qloop.core.spec import Budget, CircuitSpec, IntDomain, ParamSpace

DEFAULT_N = 12


def ghz_ladder_circuit(n: int) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    return qc


def ghz_reference_state(n: int) -> Statevector:
    data = np.zeros(2**n, dtype=complex)
    data[0] = 1.0 / np.sqrt(2)
    data[-1] = 1.0 / np.sqrt(2)
    return Statevector(data)


class GHZSpec(CircuitSpec):
    """GHZ state via a CNOT ladder (depth O(n))."""

    name = "ghz"
    n_qubits = DEFAULT_N
    tags = ["clifford", "entanglement", "topology-sensitive"]

    def build(self, n: int = DEFAULT_N, **params) -> QuantumCircuit:
        return ghz_ladder_circuit(n)

    def reference_state(self, n: int = DEFAULT_N, **params) -> Statevector:
        return ghz_reference_state(n)

    def invariants_for(self, n: int = DEFAULT_N, **params):
        checks = [normalized(), unitary()]
        # Every pair of qubits is perfectly Z-correlated on a GHZ state.
        checks.append(zz_expectation_equals(0, n - 1))
        if n > 2:
            checks.append(zz_expectation_equals(0, 1))
        return checks

    def budget(self) -> Budget:
        # Measured at n=12: sim-ideal/all-to-all depth=12-13, 2q=11;
        # sim-noisy-heavyhex depth=14, 2q=11 — the ladder is already local,
        # so heavy-hex adds almost no SWAP overhead.
        return Budget(depth=20, two_qubit_gates=15, depth_limited=25, two_qubit_gates_limited=18)

    def param_space(self) -> ParamSpace:
        return ParamSpace(n=IntDomain(2, 12))

    # expected_distribution intentionally omitted → noisy tier skips visibly.
    # To enable it, add:
    #   def expected_distribution(self, **params):
    #       return {"0" * DEFAULT_N: 0.5, "1" * DEFAULT_N: 0.5}
