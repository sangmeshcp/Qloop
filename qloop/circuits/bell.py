"""Bell state circuit plugin."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

# Import existing implementations so old tests continue to work via re-export.
from circuits.bell import bell_circuit, bell_circuit_measured  # noqa: F401
from qloop.core.invariants import normalized, unitary
from qloop.core.spec import Budget, CircuitSpec, ParamSpace


class BellSpec(CircuitSpec):
    name = "bell"
    n_qubits = 2
    tags = ["clifford", "entanglement"]

    def build(self, **params) -> QuantumCircuit:
        return bell_circuit()

    def reference_state(self, **params) -> Statevector:
        inv_sqrt2 = 1.0 / np.sqrt(2)
        return Statevector([inv_sqrt2, 0.0, 0.0, inv_sqrt2])

    def invariants(self):
        return [normalized(), unitary()]

    def budget(self) -> Budget:
        # Bell is tiny; tighter budgets catch over-decomposition early
        return Budget(depth=15, two_qubit_gates=5, depth_limited=15, two_qubit_gates_limited=5)

    def expected_distribution(self, **params) -> dict[str, float]:
        return {"00": 0.5, "11": 0.5}

    def param_space(self) -> ParamSpace:
        return ParamSpace.empty()
