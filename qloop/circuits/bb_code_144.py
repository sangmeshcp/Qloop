"""
Bivariate bicycle (BB) "gross code" syndrome extraction — [[144,12,12]].

Source: Bravyi, Cross, Gambetta, Maslov, Rall, Yoder, "High-threshold and
low-overhead fault-tolerant quantum memory," Nature 627, 778 (2024),
arXiv:2308.07915. l=12, m=6; A = x^3+y+y^2, B = y^3+x+x^2 (same generators
as bb_code_72.py's [[72,12,6]], only l changes). Construction, CSS
verification, CNOT scheduling, and Stim detector logic are all shared with
bb_code_72.py via _bb_code_common.py — see that module's docstring for the
full derivation notes (they apply identically here; the algebraic argument
for CSS commutation and the 6-tick-per-check-type schedule does not depend
on the specific values of l, m).

This is the framework's deepest transpile + property stress test: 288
physical qubits (144 data + 144 ancilla), Clifford-only so Stim-tractable,
but 12x further beyond statevector simulation than bb_code_72 already was.
Never enters the statevector tier (n_qubits > MAX_STATEVECTOR_QUBITS, so
the framework skips it automatically) — no reference_state or
expected_distribution is declared.

Measured transpile-matrix result (the headline number this circuit exists
to produce): 6n = 864 CNOTs per cycle on sim-ideal/sim-noisy-alltoall
(depth 9, matching the paper's stated 6n CNOTs/cycle exactly), vs. depth
~874 / ~17170 CNOTs on sim-noisy-heavyhex — the degree-6, non-planar
Tanner graph forces roughly 20x the two-qubit gate count once routed onto
a degree-3 heavy-hex lattice.

Known limitation (same as bb_code_72.py): circuit-level distance d_circ is
not computed — would require explicit logical-operator construction beyond
this plugin's scope. The paper reports d_circ<=10 for this code (NOT the
code distance d=12 — circuit-level distance is generally lower than code
distance for BB syndrome circuits); we do not independently verify that
figure.
"""

from __future__ import annotations

from qiskit import QuantumCircuit

from qloop.circuits._bb_code_common import BBCodeConstruction
from qloop.core.spec import Budget, ChoiceDomain, CircuitSpec, IntDomain, ParamSpace

_CODE = BBCodeConstruction(l_size=12, m_size=6, expected_k=12)


class BBCode144Spec(CircuitSpec):
    """[[144,12,12]] gross code syndrome extraction (Clifford, Stim-verified)."""

    name = "bb-code-144"
    n_qubits = _CODE.n_total
    tags = ["clifford", "qec", "bivariate-bicycle", "gross-code"]

    def build(self, **params) -> QuantumCircuit:
        return _CODE.build_circuit()

    def budget(self) -> Budget:
        # Measured: sim-ideal/sim-noisy-alltoall depth=9, 2q=864 (=6n exactly,
        # matching the paper's stated CNOT count); sim-noisy-heavyhex
        # depth~874, 2q~17170 — the sharpest topology-stress result in this
        # framework's corpus.
        return Budget(
            depth=20,
            two_qubit_gates=1000,
            depth_limited=1200,
            two_qubit_gates_limited=20000,
        )

    # No reference_state / expected_distribution: 288 qubits is far beyond
    # Statevector/Aer-statevector-sampling; verification routes through Stim.

    def stim_program(self, error_qubit: int = -1, error_basis: str = "X", **params):
        """error_qubit: data qubit index (0..143) to error, or -1 for the quiescence case."""
        return _CODE.stim_program(error_qubit, error_basis)

    def stim_param_space(self) -> ParamSpace:
        return ParamSpace(
            error_qubit=IntDomain(-1, _CODE.n_data - 1),
            error_basis=ChoiceDomain(("X", "Z")),
        )
