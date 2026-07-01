"""
Shared QAOA MaxCut helpers, used by qaoa_maxcut.py and qaoa_ring.py.

Not a CircuitSpec — the registry's discovery skips modules with no
concrete CircuitSpec subclass, so this plain helper module coexists safely
with the auto-discovered plugin files.

The exact oracle for both QAOA circuits is computed via
independent_qaoa_state(), a from-scratch numpy simulation (diagonal cost
phase + per-qubit Rx mixer) that is intentionally NOT derived from a
memorized closed-form QAOA expectation formula (e.g. the p=1
Farhi-Goldstone-Gutmann analytic result for regular graphs) — this project
does not have high enough confidence in recalling that formula's exact
combinatorial coefficients to hardcode it as a trusted "exact" reference,
so instead the reference state is obtained via a second, independent
simulation path (diagonal phase array + tensor-product mixer, no gate
circuit involved) and cross-checked against the actual Qiskit circuit.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


def cost_values(edges: list[tuple[int, int]], n: int) -> np.ndarray:
    """cost[idx] = number of edges cut by the computational basis bitstring idx."""
    dim = 2**n
    cost = np.zeros(dim)
    for idx in range(dim):
        bits = [(idx >> q) & 1 for q in range(n)]
        cost[idx] = sum(1 for u, v in edges if bits[u] != bits[v])
    return cost


def qaoa_circuit(edges: list[tuple[int, int]], n: int, gamma: float, beta: float) -> QuantumCircuit:
    """
    Single-layer (p=1) QAOA MaxCut circuit.

    Cost layer: e^{-i*gamma*C} where C = sum_edges (I - Z_u Z_v)/2 (the cut-count
    operator), realized per edge as CX(u,v) . RZ(-gamma) on v . CX(u,v),
    which implements e^{i*gamma/2*Z_u*Z_v} per edge; the circuit's
    global_phase is set explicitly to e^{-i*gamma*|E|/2} to match C's "+I/2"
    term exactly (needed for exact amplitude-level comparison against
    independent_qaoa_state() below — a fidelity-only check would silently
    ignore this and was how a missing-global-phase bug here was first
    caught: the two independent computations agreed up to global phase but
    not exactly, until this line was added). Mixer layer: RX(2*beta) on
    every qubit.
    """
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for u, v in edges:
        qc.cx(u, v)
        qc.rz(-gamma, v)
        qc.cx(u, v)
    qc.global_phase += -gamma * len(edges) / 2
    for q in range(n):
        qc.rx(2 * beta, q)
    return qc


def independent_qaoa_state(
    edges: list[tuple[int, int]], n: int, gamma: float, beta: float
) -> Statevector:
    """
    Independent numpy simulation of the same QAOA state, for exact-tier
    cross-checking against the Qiskit circuit built by qaoa_circuit().
    """
    cost = cost_values(edges, n)
    dim = 2**n
    psi = np.full(dim, 1.0 / np.sqrt(dim), dtype=complex)
    psi = psi * np.exp(-1j * gamma * cost)
    for q in range(n):
        c, s = np.cos(beta), np.sin(beta)
        new_psi = np.zeros(dim, dtype=complex)
        for idx in range(dim):
            partner = idx ^ (1 << q)
            new_psi[idx] = c * psi[idx] - 1j * s * psi[partner]
        psi = new_psi
    return Statevector(psi)


def dominant_bitstrings(
    edges: list[tuple[int, int]], n: int, gamma: float, beta: float, top: int = 2
) -> dict[str, float]:
    """Exact probabilities of the `top` highest-probability outcomes at (gamma, beta)."""
    sv = independent_qaoa_state(edges, n, gamma, beta)
    probs = sv.probabilities()
    order = np.argsort(probs)[::-1][:top]
    return {format(idx, f"0{n}b"): float(probs[idx]) for idx in order}
