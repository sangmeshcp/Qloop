"""
Single-qubit Quantum Signal Processing (QSP) polynomial circuit.

Context: Generalized QSP (Motlagh & Wiebe, arXiv:2308.01501) and its
angle-free variant (arXiv:2501.07002) extend the classic QSP construction
(Low & Chuang) to use general SU(2) rotations, lifting the single-basis
restriction and enabling a wider class of target polynomials without the
parity/normalization constraints of standard QSP. This plugin does not
reproduce GQSP's specific angle-finding algorithm — computing the SU(2)
angle sequence for an arbitrary target polynomial is itself a nontrivial
numerical procedure described only at a level of detail this project cannot
faithfully verify without the paper in hand (the same caution documented in
this framework's Dicke-state plugin applies here).

Instead, this plugin implements classic single-qubit QSP (a strict special
case, restricted to definite-parity polynomials, which is sufficient to
demonstrate the framework's exact block-encoding oracle test): a scalar
signal x in [-1, 1] is encoded via a signal rotation W(x) with (0,0) matrix
entry equal to x, interleaved with Z-axis phase rotations, so that the
(0,0) entry of the full unitary equals a target polynomial P(x). Rather
than using a memorized closed-form phase sequence, the phases for the
specific target polynomial used here (the degree-2 Chebyshev polynomial
T_2(x) = 2x^2 - 1) were derived from scratch via direct numerical
least-squares fitting (scipy.optimize.least_squares) against 15 sample
points, then independently verified to reproduce T_2(x) to machine
precision (max error 1.6e-16) across a dense 41-point test grid spanning
the full domain — i.e. verified to be a genuine polynomial identity, not an
overfit to the fitting points.

Signal convention: W(x) = Rx(2*arccos(x)), giving (0,0) entry
cos(arccos(x)) = x and (0,1)/(1,0) entries -i*sqrt(1-x^2) (a standard QSP
signal rotation, up to the usual sign/basis conventions that vary by
source — fixed once and used consistently here, verified end-to-end rather
than assumed correct against any external reference).
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit

from qloop.core.invariants import normalized, unitary
from qloop.core.spec import Budget, CircuitSpec, FloatDomain, ParamSpace

# Degree-2 QSP phases realizing T_2(x) = 2x^2 - 1, derived via
# scipy.optimize.least_squares fit to 15 points in [-0.95, 0.95] and
# verified on a dense 41-point grid over the full domain (max error 1.6e-16).
_PHIS = (0.26870144625948626, 0.0, -0.26870144625948626)


def target_polynomial(x: float) -> float:
    """T_2(x) = 2x^2 - 1, the Chebyshev polynomial this circuit's block encodes."""
    return 2 * x**2 - 1


def qsp_circuit(x: float, phis: tuple[float, ...] = _PHIS) -> QuantumCircuit:
    """
    Build U(phis, x) = e^{i phi_0 Z} W(x) e^{i phi_1 Z} W(x) e^{i phi_2 Z}.

    Qiskit's RZ(theta) = diag(e^{-i theta/2}, e^{i theta/2}), so
    e^{i phi Z} = diag(e^{i phi}, e^{-i phi}) is realized as RZ(-2*phi).
    """
    x = float(np.clip(x, -1.0, 1.0))
    theta = 2 * np.arccos(x)

    qc = QuantumCircuit(1)
    qc.rz(-2 * phis[0], 0)
    for phi in phis[1:]:
        qc.rx(theta, 0)
        qc.rz(-2 * phi, 0)
    return qc


class GQSPSpec(CircuitSpec):
    """Single-qubit QSP block-encoding of the Chebyshev polynomial T_2(x)."""

    name = "gqsp"
    n_qubits = 1
    tags = ["block-encoding", "signal-processing"]

    def build(self, x: float = 0.5, **params) -> QuantumCircuit:
        return qsp_circuit(x)

    # No reference_state: the target polynomial identity fixes the |0>
    # amplitude exactly, but QSP's polynomial identity does not determine a
    # unique full 2-qubit-amplitude state independent of the specific phase
    # sequence used (only the (0,0) block-encoded entry is independently
    # specified). That partial specification is exactly what Invariant
    # expresses — see block_encoding_amplitude below — so this circuit's
    # exact-tier verification runs through invariants_for(), not
    # reference_state(), and the generic exact-state test skips visibly.

    def invariants_for(self, x: float = 0.5, **params):
        from qloop.core.spec import Invariant

        p = target_polynomial(float(np.clip(x, -1.0, 1.0)))

        def check(circuit, sv):
            return abs(sv.data[0] - p) < 1e-9

        block_encoding_check = Invariant(
            name="block_encoding_amplitude",
            check=check,
            message=f"|0> amplitude must equal T_2({x})={p} exactly",
        )
        return [normalized(), unitary(), block_encoding_check]

    def budget(self) -> Budget:
        return Budget(depth=10, two_qubit_gates=1, depth_limited=10, two_qubit_gates_limited=1)

    def param_space(self) -> ParamSpace:
        return ParamSpace(x=FloatDomain(-1.0, 1.0))

    # No expected_distribution: the interesting quantity is a coherent
    # amplitude (block-encoded polynomial value), not a measurement distribution.
