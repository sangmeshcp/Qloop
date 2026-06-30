"""
Bivariate bicycle (BB) "gross code" syndrome extraction — [[72,12,6]].

Source: Bravyi, Cross, Gambetta, Maslov, Rall, Yoder, "High-threshold and
low-overhead fault-tolerant quantum memory," Nature 627, 778 (2024),
arXiv:2308.07915. l=m=6; A = x^3+y+y^2, B = y^3+x+x^2.

This is the framework's Clifford/QEC stress test: 144 physical qubits (72
data + 72 ancilla) is far beyond statevector simulation (2^144 amplitudes),
so this plugin is verified entirely through Stim (stim_program /
stim_param_space) rather than the statevector-based exact/property tiers,
which the framework skips automatically (n_qubits > MAX_STATEVECTOR_QUBITS).

Construction (verified at import time, not just asserted from the paper):
  - x, y are commuting cyclic shift permutations on the l*m-element grid
    Z_l x Z_m; A, B are GF(2) sums of three such permutations each, giving
    each check weight 6 (3 terms from A, 3 from B).
  - Hx = [A | B], Hz = [B^T | A^T] act on a 2lm-qubit register split into an
    "L" block (first lm qubits) and an "R" block (last lm qubits).
  - CSS commutation (Hx . Hz^T = 0 mod 2) holds automatically because x and y
    commute, so A and B commute as elements of the group algebra; this is
    checked numerically below as a guard against implementation bugs, not
    relied on as a bare assertion from the paper.
  - n=72, k=12 are independently verified via GF(2) rank of Hx, Hz.

CNOT scheduling: each of the 6 "generator" sets (3 from A, 3 from B) is, by
construction, a perfect matching between one ancilla type and one data block
(every ancilla is touched exactly once, every targeted data qubit exactly
once) — so within a generator's own tick there is never a qubit conflict.
However, ticks cannot be freely interleaved between X-type and Z-type checks
that touch the same data qubit: empirically (verified by direct simulation,
not just degree-counting), doing all Z-check CNOTs first and all X-check
CNOTs second, within each round, gives a circuit whose two-round detectors
are quiescent absent errors and fire correctly on injected errors; several
interleaved orderings that are "conflict-free" by the qubit-reuse-per-tick
criterion alone were tried first and produced spurious non-deterministic
detectors, i.e. conflict-freedom is necessary but not sufficient for
syndrome-extraction correctness. The schedule here is therefore 12 ticks (6
Z-layers + 6 X-layers) rather than the paper's reported depth-7 circuit,
which uses a more carefully interleaved schedule we did not attempt to
reproduce verbatim (we do not have independently-verified access to the
paper's literal Table 5 CNOT ordering). This is still a faithful, from-
scratch, mathematically-verified reconstruction of the code and its syndrome
circuit; only the *schedule depth* differs from the published optimum.

Known limitation: we do not compute the circuit-level distance d_circ here.
Doing so via Stim's shortest_graphlike_error requires explicit logical-
operator (OBSERVABLE_INCLUDE) construction for the code, which is a
substantial additional GF(2) nullspace computation beyond this plugin's
scope. The paper reports d_circ=6 for this code (conjectured distance-
preserving); we do not independently verify that figure.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit

from qloop.core.spec import (
    Budget,
    ChoiceDomain,
    CircuitSpec,
    IntDomain,
    ParamSpace,
)

try:
    import stim
except ImportError:  # pragma: no cover
    stim = None

L_SIZE = 6
M_SIZE = 6
LM = L_SIZE * M_SIZE  # 36
N_DATA = 2 * LM  # 72
N_TOTAL = 4 * LM  # 144 (72 data + 36 X-anc + 36 Z-anc)


def _idx(i: int, j: int) -> int:
    return i * M_SIZE + j


def _perm_x(k: int) -> list[int]:
    p = [0] * LM
    for i in range(L_SIZE):
        for j in range(M_SIZE):
            p[_idx(i, j)] = _idx((i + k) % L_SIZE, j)
    return p


def _perm_y(k: int) -> list[int]:
    p = [0] * LM
    for i in range(L_SIZE):
        for j in range(M_SIZE):
            p[_idx(i, j)] = _idx(i, (j + k) % M_SIZE)
    return p


def _inv_perm(p: list[int]) -> list[int]:
    inv = [0] * len(p)
    for i, v in enumerate(p):
        inv[v] = i
    return inv


# A's three generators (X-check support on the L data block)
_A_GROUPS = [_perm_x(3), _perm_y(1), _perm_y(2)]
# B's three generators (X-check support on the R data block)
_B_GROUPS = [_perm_y(3), _perm_x(1), _perm_x(2)]
# Hz = [B^T | A^T]: Z-check L-support uses inverse-of-B generators,
# Z-check R-support uses inverse-of-A generators.
_INV_B_FOR_L = [_inv_perm(g) for g in _B_GROUPS]
_INV_A_FOR_R = [_inv_perm(g) for g in _A_GROUPS]


def _L(j: int) -> int:
    return j


def _R(j: int) -> int:
    return LM + j


def _XA(i: int) -> int:
    return 2 * LM + i


def _ZA(i: int) -> int:
    return 2 * LM + LM + i


def _build_layers() -> tuple[list[list[tuple[int, int]]], list[list[tuple[int, int]]]]:
    """Return (z_layers, x_layers): each a list of 6 (control, target) edge lists."""
    x_layers = []
    for gen in _A_GROUPS:
        x_layers.append([(_XA(i), _L(gen[i])) for i in range(LM)])
    for gen in _B_GROUPS:
        x_layers.append([(_XA(i), _R(gen[i])) for i in range(LM)])

    z_layers = []
    for gen in _INV_B_FOR_L:
        z_layers.append([(_L(gen[i]), _ZA(i)) for i in range(LM)])
    for gen in _INV_A_FOR_R:
        z_layers.append([(_R(gen[i]), _ZA(i)) for i in range(LM)])

    return z_layers, x_layers


_Z_LAYERS, _X_LAYERS = _build_layers()


def _verify_css_construction() -> None:
    """Module-import-time structural guard: CSS commutation and code parameters."""

    def perm_to_matrix(p: list[int]) -> np.ndarray:
        mat = np.zeros((LM, LM), dtype=int)
        for row, col in enumerate(p):
            mat[row, col] = 1
        return mat

    a_mat = sum(perm_to_matrix(g) for g in _A_GROUPS) % 2
    b_mat = sum(perm_to_matrix(g) for g in _B_GROUPS) % 2
    if not (set(a_mat.sum(axis=0)) == {3} and set(a_mat.sum(axis=1)) == {3}):
        raise AssertionError("A matrix is not weight-3 regular; generator construction bug")
    if not (set(b_mat.sum(axis=0)) == {3} and set(b_mat.sum(axis=1)) == {3}):
        raise AssertionError("B matrix is not weight-3 regular; generator construction bug")

    hx = np.concatenate([a_mat, b_mat], axis=1)
    hz = np.concatenate([b_mat.T, a_mat.T], axis=1)
    if not np.all((hx @ hz.T) % 2 == 0):
        raise AssertionError("Hx . Hz^T != 0 mod 2; CSS commutation violated")

    def gf2_rank(mat: np.ndarray) -> int:
        mat = mat.copy() % 2
        rows, cols = mat.shape
        rank = 0
        for col in range(cols):
            pivot = next((r for r in range(rank, rows) if mat[r, col] == 1), None)
            if pivot is None:
                continue
            mat[[rank, pivot]] = mat[[pivot, rank]]
            for r in range(rows):
                if r != rank and mat[r, col] == 1:
                    mat[r] = (mat[r] + mat[rank]) % 2
            rank += 1
            if rank == rows:
                break
        return rank

    k = N_DATA - gf2_rank(hx) - gf2_rank(hz)
    if k != 12:
        raise AssertionError(f"Expected k=12 logical qubits, computed k={k}")


_verify_css_construction()


class BBCode72Spec(CircuitSpec):
    """[[72,12,6]] bivariate-bicycle syndrome extraction (Clifford, Stim-verified)."""

    name = "bb-code-72"
    n_qubits = N_TOTAL
    tags = ["clifford", "qec", "bivariate-bicycle"]

    def build(self, **params) -> QuantumCircuit:
        """Single round of syndrome extraction (no measurement), for lint/transpile only."""
        qc = QuantumCircuit(N_TOTAL)
        x_anc = [_XA(i) for i in range(LM)]
        qc.h(x_anc)
        for layer in _Z_LAYERS + _X_LAYERS:
            for ctrl, tgt in layer:
                qc.cx(ctrl, tgt)
        return qc

    def budget(self) -> Budget:
        # Measured: all-to-all depth=9 2q=432; heavy-hex depth~645-717 2q~6900-7000
        # (degree-6, non-planar Tanner graph forces heavy SWAP routing on
        # the degree-3 heavy-hex lattice — the headline topology-stress result).
        return Budget(
            depth=20,
            two_qubit_gates=500,
            depth_limited=900,
            two_qubit_gates_limited=7500,
        )

    # No reference_state / expected_distribution: 144 qubits is far beyond
    # Statevector/Aer-statevector-sampling; verification routes through Stim.

    def stim_program(self, error_qubit: int = -1, error_basis: str = "X", **params):
        """Two-round syndrome extraction with detectors comparing round1 vs round2.

        error_qubit: index of a DATA qubit (0..71) to apply a (p=1) Pauli error
        to between rounds, or -1 for no error (quiescence check).
        """
        if stim is None:
            return None

        x_anc = [_XA(i) for i in range(LM)]
        z_anc = [_ZA(i) for i in range(LM)]

        circuit = stim.Circuit()

        def one_round() -> None:
            circuit.append("RX", x_anc)
            circuit.append("R", z_anc)
            for layer in _Z_LAYERS:
                for ctrl, tgt in layer:
                    circuit.append("CX", [ctrl, tgt])
            for layer in _X_LAYERS:
                for ctrl, tgt in layer:
                    circuit.append("CX", [ctrl, tgt])
            circuit.append("MX", x_anc)
            circuit.append("M", z_anc)

        one_round()
        if error_qubit >= 0:
            gate = "X_ERROR" if error_basis == "X" else "Z_ERROR"
            circuit.append(gate, [error_qubit], 1.0)
        one_round()

        meas_per_round = LM + LM
        total_meas = 2 * meas_per_round
        round2_start = meas_per_round
        for i in range(LM):
            r1, r2 = i, round2_start + i
            circuit.append(
                "DETECTOR",
                [stim.target_rec(-(total_meas - r1)), stim.target_rec(-(total_meas - r2))],
            )
        for i in range(LM):
            r1, r2 = LM + i, round2_start + LM + i
            circuit.append(
                "DETECTOR",
                [stim.target_rec(-(total_meas - r1)), stim.target_rec(-(total_meas - r2))],
            )
        return circuit

    def stim_param_space(self) -> ParamSpace:
        # error_qubit=-1 is the "no error" quiescence case; 0..71 inject on a data qubit.
        return ParamSpace(
            error_qubit=IntDomain(-1, N_DATA - 1),
            error_basis=ChoiceDomain(("X", "Z")),
        )
