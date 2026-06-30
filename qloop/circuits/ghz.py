"""
GHZ state circuit plugin — framework proof-of-concept.

This file is the ONLY thing needed to add a new circuit to the full pipeline.
After dropping it in qloop/circuits/, pytest automatically:
  ✓ exact-tests it (reference_state is defined)
  ✓ checks normalization and unitarity (invariants)
  ✓ transpiles it across all three targets (budget defined)
  ✗ skips the noisy tier with a visible reason (no expected_distribution)
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qloop.core.invariants import normalized, unitary
from qloop.core.spec import Budget, CircuitSpec


class GHZSpec(CircuitSpec):
    """GHZ state: (|000⟩ + |111⟩) / √2."""

    name = "ghz"
    n_qubits = 3
    tags = ["clifford", "entanglement"]

    def build(self, **params) -> QuantumCircuit:
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.cx(0, 1)
        qc.cx(1, 2)
        return qc

    def reference_state(self, **params) -> Statevector:
        data = np.zeros(8, dtype=complex)
        data[0] = 1.0 / np.sqrt(2)   # |000⟩
        data[7] = 1.0 / np.sqrt(2)   # |111⟩
        return Statevector(data)

    def invariants(self):
        return [normalized(), unitary()]

    def budget(self) -> Budget:
        return Budget(
            depth=10,
            two_qubit_gates=5,
            depth_limited=25,  # routing on heavy-hex may add 1 SWAP
            two_qubit_gates_limited=10,
        )

    # expected_distribution intentionally omitted → noisy tier skips visibly.
    # To enable it, add:
    #   def expected_distribution(self, **params):
    #       return {"000": 0.5, "111": 0.5}
