"""
Shared bivariate-bicycle (BB) QEC code construction, parametrized by (l, m).

Not a CircuitSpec — the registry's discovery skips modules with no concrete
CircuitSpec subclass, so this shared logic coexists safely with the
auto-discovered bb_code_72.py / bb_code_144.py plugin files, which each
instantiate BBCodeConstruction(l, m, expected_k) and wire up a thin
CircuitSpec around it.

Source: Bravyi, Cross, Gambetta, Maslov, Rall, Yoder, "High-threshold and
low-overhead fault-tolerant quantum memory," Nature 627, 778 (2024),
arXiv:2308.07915. A = x^3+y+y^2, B = y^3+x+x^2 (fixed for both code
instances; l, m vary: l=m=6 for [[72,12,6]], l=12, m=6 for [[144,12,12]]).

See qloop/circuits/bb_code_72.py's module docstring for the full derivation
notes (CSS commutation, the 12-tick Z-then-X CNOT schedule, and why it
differs from the paper's depth-7 schedule, and the d_circ limitation) — all
apply identically here since the algebraic argument does not depend on the
specific values of l, m, only on x and y being commuting cyclic shifts.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit

try:
    import stim
except ImportError:  # pragma: no cover
    stim = None


def _idx(i: int, j: int, m_size: int) -> int:
    return i * m_size + j


def _perm_x(k: int, l_size: int, m_size: int) -> list[int]:
    p = [0] * (l_size * m_size)
    for i in range(l_size):
        for j in range(m_size):
            p[_idx(i, j, m_size)] = _idx((i + k) % l_size, j, m_size)
    return p


def _perm_y(k: int, l_size: int, m_size: int) -> list[int]:
    p = [0] * (l_size * m_size)
    for i in range(l_size):
        for j in range(m_size):
            p[_idx(i, j, m_size)] = _idx(i, (j + k) % m_size, m_size)
    return p


def _inv_perm(p: list[int]) -> list[int]:
    inv = [0] * len(p)
    for i, v in enumerate(p):
        inv[v] = i
    return inv


class BBCodeConstruction:
    """Derives, verifies, and schedules a BB code's syndrome-extraction circuit."""

    def __init__(self, l_size: int, m_size: int, expected_k: int) -> None:
        self.l_size = l_size
        self.m_size = m_size
        self.lm = l_size * m_size
        self.n_data = 2 * self.lm
        self.n_total = 4 * self.lm

        self.a_groups = [
            _perm_x(3, l_size, m_size),
            _perm_y(1, l_size, m_size),
            _perm_y(2, l_size, m_size),
        ]
        self.b_groups = [
            _perm_y(3, l_size, m_size),
            _perm_x(1, l_size, m_size),
            _perm_x(2, l_size, m_size),
        ]
        inv_b_for_l = [_inv_perm(g) for g in self.b_groups]
        inv_a_for_r = [_inv_perm(g) for g in self.a_groups]

        lm = self.lm
        self.L = lambda j: j
        self.R = lambda j: lm + j
        self.XA = lambda i: 2 * lm + i
        self.ZA = lambda i: 2 * lm + lm + i

        x_layers = [[(self.XA(i), self.L(gen[i])) for i in range(lm)] for gen in self.a_groups]
        x_layers += [[(self.XA(i), self.R(gen[i])) for i in range(lm)] for gen in self.b_groups]
        z_layers = [[(self.L(gen[i]), self.ZA(i)) for i in range(lm)] for gen in inv_b_for_l]
        z_layers += [[(self.R(gen[i]), self.ZA(i)) for i in range(lm)] for gen in inv_a_for_r]
        self.x_layers = x_layers
        self.z_layers = z_layers

        self.k = self._verify(expected_k)

    def _verify(self, expected_k: int) -> int:
        lm = self.lm

        def perm_to_matrix(p: list[int]) -> np.ndarray:
            mat = np.zeros((lm, lm), dtype=int)
            for row, col in enumerate(p):
                mat[row, col] = 1
            return mat

        a_mat = sum(perm_to_matrix(g) for g in self.a_groups) % 2
        b_mat = sum(perm_to_matrix(g) for g in self.b_groups) % 2
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

        k = self.n_data - gf2_rank(hx) - gf2_rank(hz)
        if k != expected_k:
            raise AssertionError(f"Expected k={expected_k} logical qubits, computed k={k}")
        return k

    def build_circuit(self) -> QuantumCircuit:
        """Single round of syndrome extraction (no measurement), for lint/transpile only."""
        qc = QuantumCircuit(self.n_total)
        x_anc = [self.XA(i) for i in range(self.lm)]
        qc.h(x_anc)
        for layer in self.z_layers + self.x_layers:
            for ctrl, tgt in layer:
                qc.cx(ctrl, tgt)
        return qc

    def stim_program(self, error_qubit: int = -1, error_basis: str = "X"):
        """Two-round syndrome extraction with detectors comparing round1 vs round2."""
        if stim is None:
            return None

        lm = self.lm
        x_anc = [self.XA(i) for i in range(lm)]
        z_anc = [self.ZA(i) for i in range(lm)]
        circuit = stim.Circuit()

        def one_round() -> None:
            circuit.append("RX", x_anc)
            circuit.append("R", z_anc)
            for layer in self.z_layers:
                for ctrl, tgt in layer:
                    circuit.append("CX", [ctrl, tgt])
            for layer in self.x_layers:
                for ctrl, tgt in layer:
                    circuit.append("CX", [ctrl, tgt])
            circuit.append("MX", x_anc)
            circuit.append("M", z_anc)

        one_round()
        if error_qubit >= 0:
            gate = "X_ERROR" if error_basis == "X" else "Z_ERROR"
            circuit.append(gate, [error_qubit], 1.0)
        one_round()

        meas_per_round = lm + lm
        total_meas = 2 * meas_per_round
        round2_start = meas_per_round
        for i in range(lm):
            r1, r2 = i, round2_start + i
            circuit.append(
                "DETECTOR",
                [stim.target_rec(-(total_meas - r1)), stim.target_rec(-(total_meas - r2))],
            )
        for i in range(lm):
            r1, r2 = lm + i, round2_start + lm + i
            circuit.append(
                "DETECTOR",
                [stim.target_rec(-(total_meas - r1)), stim.target_rec(-(total_meas - r2))],
            )
        return circuit
