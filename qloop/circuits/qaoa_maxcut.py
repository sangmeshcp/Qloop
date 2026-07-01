"""
QAOA MaxCut on K_{3,3} (complete bipartite, 3-regular, non-planar coupling).

Context: recent Pauli-exponentiation compilation research (e.g. PHOENIX,
arXiv:2504.03529) targets Hamiltonian-simulation/QAOA programs expressed as
Pauli exponentials on heavy-hex hardware. This plugin does not reproduce
that paper's Pauli-IR compilation algorithm — it implements the standard
single-layer (p=1) QAOA MaxCut ansatz that such a compiler would take as
*input*, on a graph (K_{3,3}) chosen specifically because its edges are not
local to any simple 1D/2D qubit layout, making it a genuine topology-stress
circuit for the transpile-matrix tier (contrast with qaoa_ring.py, whose
cycle-graph edges map onto a coupling map with far less SWAP overhead).

Exact oracle: see _qaoa_common.py — the target state is computed via an
independent numpy simulation (diagonal cost phase + tensor-product mixer),
not a memorized closed-form QAOA expectation formula.
"""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qloop.circuits._qaoa_common import dominant_bitstrings, independent_qaoa_state, qaoa_circuit
from qloop.core.invariants import normalized, unitary
from qloop.core.spec import Budget, CircuitSpec, FloatDomain, ParamSpace

N = 6
EDGES = [(0, 3), (0, 4), (0, 5), (1, 3), (1, 4), (1, 5), (2, 3), (2, 4), (2, 5)]

# p=1 angles found via classical optimization of the independent simulation
# (scipy.optimize.minimize, multi-start Nelder-Mead) — not a closed-form
# analytic optimum. Expectation ~6.23 out of a max possible cut of 9.
DEFAULT_GAMMA = 2.52612642
DEFAULT_BETA = 0.39269488


class QAOAMaxCutSpec(CircuitSpec):
    """Single-layer QAOA MaxCut on the K_{3,3} graph (6 qubits, degree 3)."""

    name = "qaoa-maxcut"
    n_qubits = N
    tags = ["qaoa", "combinatorial-optimization", "topology-sensitive"]

    def build(self, gamma: float = DEFAULT_GAMMA, beta: float = DEFAULT_BETA, **params) -> QuantumCircuit:
        return qaoa_circuit(EDGES, N, gamma, beta)

    def reference_state(self, gamma: float = DEFAULT_GAMMA, beta: float = DEFAULT_BETA, **params) -> Statevector:
        return independent_qaoa_state(EDGES, N, gamma, beta)

    def invariants(self):
        return [normalized(), unitary()]

    def budget(self) -> Budget:
        # Measured: sim-ideal/all-to-all depth=17-20, 2q=18; heavy-hex
        # depth~48, 2q~26 — K_{3,3}'s non-local edges cost real SWAP overhead
        # even at only 6 qubits.
        return Budget(depth=40, two_qubit_gates=25, depth_limited=90, two_qubit_gates_limited=45)

    def expected_distribution(self, gamma: float = DEFAULT_GAMMA, beta: float = DEFAULT_BETA, **params):
        return dominant_bitstrings(EDGES, N, gamma, beta, top=2)

    def param_space(self) -> ParamSpace:
        return ParamSpace(gamma=FloatDomain(0.0, 6.283185307179586), beta=FloatDomain(0.0, 3.141592653589793))
