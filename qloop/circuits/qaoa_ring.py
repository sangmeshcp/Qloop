"""
QAOA MaxCut on a 6-cycle (ring graph, degree 2, nearest-neighbor coupling).

Context: motivated by "SWAP-free" / linear-connectivity QAOA compilation
research (e.g. arXiv:2509.17296) — this plugin does not reproduce that
paper's specific compilation technique, but implements a graph instance
(a simple cycle) whose edges are ALL nearest-neighbor under a ring/linear
qubit layout, so the standard QAOA ansatz naturally incurs far less SWAP
overhead on heavy-hex than a non-local graph. Paired with qaoa_maxcut.py
(K_{3,3}, same qubit count, same ansatz structure, but non-local edges),
this is the direct topology-sensitivity contrast: same algorithm, same
size, different graph locality, different transpile cost.

Exact oracle: see _qaoa_common.py (independent numpy simulation, not a
memorized closed-form QAOA formula).
"""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qloop.circuits._qaoa_common import dominant_bitstrings, independent_qaoa_state, qaoa_circuit
from qloop.core.invariants import normalized, unitary
from qloop.core.spec import Budget, CircuitSpec, FloatDomain, ParamSpace

N = 6
EDGES = [(i, (i + 1) % N) for i in range(N)]

# p=1 angles found via classical optimization of the independent simulation.
# C_6 is bipartite, so the max cut (6, i.e. every edge cut) is achieved by
# the two alternating colorings; expectation at these angles is exactly 4.5.
DEFAULT_GAMMA = 2.35618725
DEFAULT_BETA = 1.17810813


class QAOARingSpec(CircuitSpec):
    """Single-layer QAOA MaxCut on a 6-cycle graph (6 qubits, degree 2, local edges)."""

    name = "qaoa-ring"
    n_qubits = N
    tags = ["qaoa", "combinatorial-optimization", "topology-sensitive"]

    def build(self, gamma: float = DEFAULT_GAMMA, beta: float = DEFAULT_BETA, **params) -> QuantumCircuit:
        return qaoa_circuit(EDGES, N, gamma, beta)

    def reference_state(self, gamma: float = DEFAULT_GAMMA, beta: float = DEFAULT_BETA, **params) -> Statevector:
        return independent_qaoa_state(EDGES, N, gamma, beta)

    def invariants(self):
        return [normalized(), unitary()]

    def budget(self) -> Budget:
        # Measured: sim-ideal/all-to-all depth=20-23, 2q=12; heavy-hex
        # depth~41, 2q~21 — noticeably less SWAP overhead than K_{3,3}
        # (qaoa-maxcut) at the same qubit count, since every edge is local.
        return Budget(depth=35, two_qubit_gates=18, depth_limited=70, two_qubit_gates_limited=35)

    def expected_distribution(self, gamma: float = DEFAULT_GAMMA, beta: float = DEFAULT_BETA, **params):
        return dominant_bitstrings(EDGES, N, gamma, beta, top=2)

    def param_space(self) -> ParamSpace:
        return ParamSpace(gamma=FloatDomain(0.0, 6.283185307179586), beta=FloatDomain(0.0, 3.141592653589793))
