"""
Deterministic Dicke state |D^n_k> preparation.

Dicke states are relevant to recent depth-reduction research — e.g. Yuan &
Zhang, "Depth-Efficient Quantum Circuit Synthesis for Deterministic Dicke
State Preparation," arXiv:2505.15413 (May 2025), and the constant-depth
follow-up (Vasconcelos & Joshi, arXiv:2601.10693) — both targeting the exact
state prepared here but via asymptotically shallower circuits than the one
below.

Scope note: this plugin does NOT reproduce either paper's specific novel
gate-level construction. Reconstructing an unfamiliar paper's exact circuit
from a brief description carries real risk of silently getting the
algorithm wrong (a lesson learned the hard way elsewhere in this framework's
QEC syndrome-extraction circuit, where a schedule that looked correct by a
simple counting argument turned out to produce non-deterministic syndromes
until verified by direct simulation). Rather than presenting an unverified
reconstruction as if it were the paper's algorithm, this plugin implements a
straightforward, exactly-correct-by-construction circuit derived from the
Dicke state's own recursive/hypergeometric structure, verified directly
against the closed-form target amplitude for every tested (n, k) — at the
cost of asymptotic depth efficiency (this construction is O(2^n) gates in
the worst case, not the papers' O(poly(n)) — kept to small n accordingly).

Construction: process qubits 0..n-1 in order. Before processing qubit i, let
c be the (classical, not yet measured — this is realized by branching on
every possible c via controlled gates) number of qubits among 0..i-1 that
are 1. The conditional probability that qubit i is 1, given c and k total
ones needed across n qubits, is p = (k-c)/(n-i) (a hypergeometric
conditional). For each reachable c, a controlled-Ry(2*arccos(sqrt(1-p)))
gate — or a controlled-X when p=1 — is applied to qubit i, with one open/
closed-control instance per length-i bitstring of Hamming weight c (there
are C(i,c) such bitstrings; each needs its own gate since "controlled on
exactly c ones" is not a primitive gate). This exactly reproduces the
Dicke state's amplitude structure: 1/sqrt(C(n,k)) on every weight-k
computational basis string, zero elsewhere.
"""

from __future__ import annotations

import itertools
from math import comb

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import RYGate
from qiskit.quantum_info import Statevector

from qloop.core.invariants import hamming_weight_exact, normalized, real_nonnegative_amplitudes
from qloop.core.spec import Budget, CircuitSpec, IntDomain, ParamSpace

DEFAULT_N = 6
DEFAULT_K = 3


def dicke_circuit(n: int, k: int) -> QuantumCircuit:
    """Build the n-qubit Dicke state |D^n_k> via conditional hypergeometric rotations."""
    if not (0 <= k <= n):
        raise ValueError(f"require 0 <= k <= n, got n={n}, k={k}")

    qc = QuantumCircuit(n)
    if k == 0:
        return qc
    if k == n:
        qc.x(range(n))
        return qc

    for i in range(n):
        remaining_qubits = n - i
        max_c = min(i, k)
        for c in range(max_c + 1):
            ones_needed_remaining = k - c
            if ones_needed_remaining < 0 or ones_needed_remaining > remaining_qubits:
                continue  # unreachable branch: amplitude is already exactly zero
            p1 = ones_needed_remaining / remaining_qubits
            if p1 <= 0.0:
                continue

            if p1 >= 1.0:
                # Deterministic: qubit i must be 1 whenever exactly c ones precede it.
                if i == 0:
                    qc.x(0)
                else:
                    for combo in itertools.combinations(range(i), c):
                        _append_controlled(qc, RYGate(np.pi), i, combo)
                continue

            theta = 2 * np.arccos(np.sqrt(1 - p1))
            if i == 0:
                qc.ry(theta, 0)
            else:
                for combo in itertools.combinations(range(i), c):
                    _append_controlled(qc, RYGate(theta), i, combo)
    return qc


def _append_controlled(qc: QuantumCircuit, base_gate, target: int, ones_at: tuple[int, ...]) -> None:
    """Append base_gate on `target`, controlled on qubits 0..target-1 matching ones_at exactly."""
    ctrl_qubits = list(range(target))
    ctrl_state = "".join(reversed(["1" if q in ones_at else "0" for q in ctrl_qubits]))
    gate = base_gate.control(len(ctrl_qubits), ctrl_state=ctrl_state, annotated=False)
    qc.append(gate, ctrl_qubits + [target])


class DickeSpec(CircuitSpec):
    """Deterministic Dicke state |D^n_k> for fixed n, sweeping k over [0, n]."""

    name = "dicke"
    n_qubits = DEFAULT_N
    tags = ["state-preparation", "symmetric"]

    def build(self, k: int = DEFAULT_K, **params) -> QuantumCircuit:
        return dicke_circuit(DEFAULT_N, k)

    def reference_state(self, k: int = DEFAULT_K, **params) -> Statevector:
        n = DEFAULT_N
        dim = 2**n
        amp = 1.0 / np.sqrt(comb(n, k)) if comb(n, k) > 0 else 0.0
        data = np.zeros(dim, dtype=complex)
        for idx in range(dim):
            if bin(idx).count("1") == k:
                data[idx] = amp
        return Statevector(data)

    def invariants_for(self, k: int = DEFAULT_K, **params):
        return [
            normalized(),
            hamming_weight_exact(k),
            real_nonnegative_amplitudes(),
        ]

    def budget(self) -> Budget:
        # Measured at default (n=6, k=3): sim-ideal depth=34 (multi-controlled
        # Ry gates left opaque, no basis_gates constraint); sim-noisy-alltoall
        # depth~1409/812 2q; sim-noisy-heavyhex depth~2619/1437 2q. This
        # construction is not depth-optimal (see module docstring) — budgets
        # reflect that honestly rather than papering over it with a tight limit.
        return Budget(
            depth=1600,
            two_qubit_gates=900,
            depth_limited=3000,
            two_qubit_gates_limited=1600,
        )

    def param_space(self) -> ParamSpace:
        return ParamSpace(k=IntDomain(0, DEFAULT_N))

    # No expected_distribution: Dicke states have k+1... actually up to
    # C(n,k) equally-likely bitstrings, not a small fixed set of dominant
    # outcomes — not a natural fit for the noisy tier's tolerance-band check.
