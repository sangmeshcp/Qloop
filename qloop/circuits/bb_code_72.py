"""
Bivariate bicycle (BB) code syndrome extraction — [[72,12,6]].

Source: Bravyi, Cross, Gambetta, Maslov, Rall, Yoder, "High-threshold and
low-overhead fault-tolerant quantum memory," Nature 627, 778 (2024),
arXiv:2308.07915. l=m=6; A = x^3+y+y^2, B = y^3+x+x^2. Construction shared
with bb_code_144.py ([[144,12,12]], l=12, m=6) via _bb_code_common.py.

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
    checked numerically (in _bb_code_common.BBCodeConstruction) as a guard
    against implementation bugs, not relied on as a bare assertion from the
    paper.
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

from qiskit import QuantumCircuit

from qloop.circuits._bb_code_common import BBCodeConstruction
from qloop.core.spec import Budget, ChoiceDomain, CircuitSpec, IntDomain, ParamSpace

_CODE = BBCodeConstruction(l_size=6, m_size=6, expected_k=12)


class BBCode72Spec(CircuitSpec):
    """[[72,12,6]] bivariate-bicycle syndrome extraction (Clifford, Stim-verified)."""

    name = "bb-code-72"
    n_qubits = _CODE.n_total
    tags = ["clifford", "qec", "bivariate-bicycle"]

    def build(self, **params) -> QuantumCircuit:
        return _CODE.build_circuit()

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
        """error_qubit: data qubit index (0..71) to error, or -1 for the quiescence case."""
        return _CODE.stim_program(error_qubit, error_basis)

    def stim_param_space(self) -> ParamSpace:
        return ParamSpace(
            error_qubit=IntDomain(-1, _CODE.n_data - 1),
            error_basis=ChoiceDomain(("X", "Z")),
        )
