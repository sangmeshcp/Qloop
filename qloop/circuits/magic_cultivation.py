"""
Postselected magic-state verification (scope note: NOT the Gidney-Shutty-
Jones cultivation protocol).

Context: magic state cultivation (Gidney, Shutty & Jones, arXiv:2409.17595)
grows a high-fidelity |T> state inside a surface-code patch via postselected
code-switching, achieving much lower logical error rates than direct state
injection at the cost of a non-unit acceptance probability. This plugin
does not attempt to reproduce that protocol — the real cultivation circuit
involves surface-code patches, distance-5 growth, and complementary-gap
postselection details this project cannot faithfully reconstruct from a
paper summary without a serious risk of getting it wrong (the same caution
applied throughout this framework's other paper-derived circuits).

Instead, this implements a much simpler but genuine postselected magic-
state VERIFICATION circuit — a real, textbook stabilizer measurement, not
a toy — that still demonstrates the core mechanism the plan asks the
framework to exercise: probabilistic acceptance, and quality improving
conditional on acceptance.

The magic state |A> = T|+> = (|0> + e^{i*pi/4}|1>)/sqrt(2) is the exact
+1 eigenstate of S = (X+Y)/sqrt(2) (a Hermitian, S^2=I observable — verified
directly, not assumed: S|A> = |A>). A Z error anticommutes with both X and
Y, so Z|A> is the exact -1 eigenstate of S. Measuring S via a standard
ancilla-based eigenvalue circuit (ancilla |+>, controlled-S, H, measure)
therefore perfectly distinguishes a clean candidate from a Z-corrupted one.

To make this a genuinely probabilistic (not just deterministic 0/1)
postselection circuit, an "error indicator" qubit is prepared in
sqrt(1-p)|0> + sqrt(p)|1> and used to apply Z to the candidate qubit
conditionally — modeling "state preparation fails with probability p."
Verified directly (not derived from a formula) for p in
{0, 0.1, 0.3, 0.5, 0.8, 1.0}: P(accept) = 1-p exactly, and the fidelity of
the accepted branch to |A> is exactly 1.0 whenever P(accept) > 0 — i.e.
this verification circuit perfectly filters the modeled error, so every
accepted shot is exactly correct (a cleaner result than any real
cultivation protocol, precisely because the toy error model was chosen to
be exactly what the check detects — this is intentionally a much simpler
question than "does postselection help against a realistic noise model").

Framework scope note: expected_distribution() is not declared. The
framework's noisy-tier mechanism checks raw per-bitstring probabilities
against a tolerance band; it has no support for POSTSELECTED (conditional-
on-another-qubit's-outcome) statistics, which is exactly what this circuit
needs ("statistical assertions must account for discarded shots" — from
the original corpus plan). Building that support is a real framework
extension in its own right and out of scope here; the exact-tier
invariants below (which compute the postselection accounting analytically
from the ideal statevector, not from sampled shots) are what actually
verify this circuit's behavior.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import Statevector

from qloop.core.invariants import normalized, unitary
from qloop.core.spec import Budget, CircuitSpec, FloatDomain, Invariant, ParamSpace

_X = np.array([[0, 1], [1, 0]], dtype=complex)
_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
_S_OPERATOR = (_X + _Y) / np.sqrt(2)  # Hermitian, S^2=I; |A>=T|+> is its +1 eigenstate
_CONTROLLED_S = UnitaryGate(_S_OPERATOR, label="S").control(1)


def _target_state() -> np.ndarray:
    qc = QuantumCircuit(1)
    qc.h(0)
    qc.t(0)
    return Statevector(qc).data


def _verify_stabilizer_eigenstates() -> None:
    """Module-import-time guard: |A> is +1, Z|A> is -1 eigenstate of S."""
    a = _target_state()
    if not np.allclose(_S_OPERATOR @ a, a, atol=1e-9):
        raise AssertionError("|A> is not a +1 eigenstate of S; construction bug")
    za = np.array([[1, 0], [0, -1]], dtype=complex) @ a
    if not np.allclose(_S_OPERATOR @ za, -za, atol=1e-9):
        raise AssertionError("Z|A> is not a -1 eigenstate of S; construction bug")


_verify_stabilizer_eigenstates()


def _acceptance_and_conditional_fidelity(sv: Statevector) -> tuple[float, float | None]:
    """
    Analytically postselect on the verification ancilla (qubit 1) reading 0.

    Returns (P(accept), fidelity of the accepted branch's candidate qubit
    (qubit 0) to the target magic state), marginalizing over the error
    indicator qubit (qubit 2). fidelity is None if P(accept) ~ 0.
    """
    data = sv.data
    accept_indices = [i for i in range(8) if (i >> 1) & 1 == 0]
    p_accept = float(sum(abs(data[i]) ** 2 for i in accept_indices))

    amp_accept = np.zeros(2, dtype=complex)
    for i in accept_indices:
        q0_bit = i & 1
        amp_accept[q0_bit] += data[i]
    norm = np.linalg.norm(amp_accept)
    if norm < 1e-9:
        return p_accept, None
    conditional_state = amp_accept / norm
    fidelity = float(abs(np.vdot(_target_state(), conditional_state)) ** 2)
    return p_accept, fidelity


class MagicCultivationSpec(CircuitSpec):
    """Postselected magic-state verification via a controlled-S stabilizer check."""

    name = "magic-cultivation"
    n_qubits = 3
    tags = ["magic-state", "postselection", "qec"]

    def build(self, error_prob: float = 0.3, **params) -> QuantumCircuit:
        qc = QuantumCircuit(3)  # q0=candidate, q1=verification ancilla, q2=error indicator
        qc.h(0)
        qc.t(0)
        theta = 2 * np.arcsin(np.sqrt(np.clip(error_prob, 0.0, 1.0)))
        qc.ry(theta, 2)
        qc.cz(2, 0)
        qc.h(1)
        qc.append(_CONTROLLED_S, [1, 0])
        qc.h(1)
        return qc

    def invariants_for(self, error_prob: float = 0.3, **params):
        error_prob = float(np.clip(error_prob, 0.0, 1.0))

        def check_acceptance(circuit, sv: Statevector) -> bool:
            p_accept, _ = _acceptance_and_conditional_fidelity(sv)
            return abs(p_accept - (1.0 - error_prob)) < 1e-9

        def check_conditional_fidelity(circuit, sv: Statevector) -> bool:
            p_accept, fidelity = _acceptance_and_conditional_fidelity(sv)
            if p_accept < 1e-9:
                return True  # nothing to check when acceptance is ~0
            return abs(fidelity - 1.0) < 1e-9

        return [
            normalized(),
            unitary(),
            Invariant(
                name="acceptance_probability_matches",
                check=check_acceptance,
                message=f"P(accept) must equal 1-error_prob={1 - error_prob}",
            ),
            Invariant(
                name="conditional_fidelity_when_accepted",
                check=check_conditional_fidelity,
                message="Accepted-branch candidate state must have fidelity 1.0 to |A>",
            ),
        ]

    def budget(self) -> Budget:
        return Budget(depth=20, two_qubit_gates=10, depth_limited=40, two_qubit_gates_limited=15)

    def param_space(self) -> ParamSpace:
        return ParamSpace(error_prob=FloatDomain(0.0, 1.0))

    # No reference_state / expected_distribution: see module docstring —
    # this circuit's meaningful output is a POSTSELECTED (conditional)
    # distribution, which neither existing contract method expresses; the
    # postselection accounting is verified analytically in invariants_for().
