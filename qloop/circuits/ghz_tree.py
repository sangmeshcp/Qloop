"""
GHZ state circuit plugin — log-depth CNOT-tree construction.

Same target state as ghz.py (a CNOT ladder), same default qubit count
(12), deliberately different gate structure: H on qubit 0, then repeated
doubling — at each step, every qubit entangled so far gets a CNOT to a
qubit `step` positions ahead (step = 1, 2, 4, ...) — giving depth O(log n)
instead of ladder's O(n). Verified exactly against the same closed-form
GHZ state for n up to 12 before relying on it.

Measured result, and why it's worth stating plainly rather than assuming
"shallower is better": at n=12, pre-transpile depth is 5 (tree) vs 12
(ladder) — a real logical-depth win. But post-transpile on heavy-hex, the
tree costs MORE two-qubit gates (21 vs 11) at almost the same depth (13 vs
14), because its later CNOTs connect qubits far apart in index (e.g. qubit
0 to qubit 8 in one step), which are not physically adjacent on any
line/hex-like coupling map and need SWAP routing — while the ladder's
CNOTs are already nearest-neighbor and route almost for free. This is
exactly the transpile-matrix stage's reason for existing: a circuit's
logical structure and its post-transpile hardware cost can point in
opposite directions, and only measuring the latter tells you which one is
actually cheaper to run.
"""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qloop.circuits.ghz import ghz_reference_state
from qloop.core.invariants import normalized, unitary, zz_expectation_equals
from qloop.core.spec import Budget, CircuitSpec, IntDomain, ParamSpace

DEFAULT_N = 12


def ghz_tree_circuit(n: int) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    qc.h(0)
    entangled = [0]
    step = 1
    while step < n:
        new_targets = []
        for src in list(entangled):
            tgt = src + step
            if tgt < n:
                qc.cx(src, tgt)
                new_targets.append(tgt)
        entangled.extend(new_targets)
        step *= 2
    return qc


class GHZTreeSpec(CircuitSpec):
    """GHZ state via a log-depth CNOT tree (depth O(log n)) — contrast with ghz.py's ladder."""

    name = "ghz-tree"
    n_qubits = DEFAULT_N
    tags = ["clifford", "entanglement", "topology-sensitive"]

    def build(self, n: int = DEFAULT_N, **params) -> QuantumCircuit:
        return ghz_tree_circuit(n)

    def reference_state(self, n: int = DEFAULT_N, **params) -> Statevector:
        return ghz_reference_state(n)

    def invariants_for(self, n: int = DEFAULT_N, **params):
        checks = [normalized(), unitary(), zz_expectation_equals(0, n - 1)]
        if n > 2:
            checks.append(zz_expectation_equals(0, 1))
        return checks

    def budget(self) -> Budget:
        # Measured at n=12: sim-ideal/all-to-all depth=5-6, 2q=11;
        # sim-noisy-heavyhex depth=13, 2q=21 — see module docstring: the
        # tree's long-range CNOTs cost MORE 2Q gates on heavy-hex than the
        # ladder's, despite half the logical depth.
        return Budget(depth=15, two_qubit_gates=15, depth_limited=25, two_qubit_gates_limited=30)

    def param_space(self) -> ParamSpace:
        return ParamSpace(n=IntDomain(2, 12))

    # No expected_distribution: same reasoning as ghz.py.
