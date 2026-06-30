"""
Copy this file to qloop/circuits/my_circuit.py and fill in the TODOs.

Minimum viable plugin — only the items marked REQUIRED need editing.
Every optional section has a comment explaining what it enables.
"""

from __future__ import annotations

from qiskit import QuantumCircuit

from qloop.core.invariants import normalized  # add more from invariants.py as needed
from qloop.core.spec import Budget, CircuitSpec


class MyCircuitSpec(CircuitSpec):
    # ── REQUIRED ──────────────────────────────────────────────────────────────

    name = "my-circuit"      # TODO: unique identifier (lowercase, hyphens ok)
    n_qubits = 2             # TODO: number of qubits build() produces

    # Optional: category labels for registry.by_tag() queries
    tags = ["example"]       # TODO: e.g. ["clifford", "entanglement"]

    def build(self, **params) -> QuantumCircuit:
        # TODO: construct and return your circuit (no measurements)
        qc = QuantumCircuit(self.n_qubits)
        # qc.h(0)
        # qc.cx(0, 1)
        return qc

    # ── OPTIONAL: exact tier (Stage 2) ────────────────────────────────────────
    # Define reference_state() to enable statevector comparison.
    # Omit it and this stage skips with a visible reason.

    # def reference_state(self, **params) -> Statevector:
    #     # TODO: return the exact output statevector
    #     inv_sqrt2 = 1.0 / np.sqrt(2)
    #     return Statevector([inv_sqrt2, 0.0, 0.0, inv_sqrt2])

    # ── OPTIONAL: property tier (Stage 3) ─────────────────────────────────────
    # Define invariants() for parameter-independent checks.
    # normalized() is checked automatically regardless.

    def invariants(self):
        return [normalized()]
        # Add: unitary(), marked_dominant("01", 0.5), etc.

    # ── REQUIRED: transpile tier (Stage 4) ────────────────────────────────────
    # Budget defines the max depth/gate-count after transpilation.
    # Use depth_limited / two_qubit_gates_limited for heavy-hex overhead.

    def budget(self) -> Budget:
        return Budget(
            depth=50,                 # TODO: tune to your circuit's complexity
            two_qubit_gates=15,
            depth_limited=80,         # heavy-hex SWAP overhead
            two_qubit_gates_limited=25,
        )

    # ── OPTIONAL: noisy tier (Stage 5) ────────────────────────────────────────
    # Define expected_distribution() to enable statistical tolerance-band checks.
    # Omit it and the noisy tier skips with a visible reason (like GHZ).

    # def expected_distribution(self, **params) -> dict[str, float]:
    #     # TODO: ideal probabilities — must sum to ≤ 1.0
    #     return {"00": 0.5, "11": 0.5}

    # ── OPTIONAL: param sweep (Stage 3 hypothesis fuzzing) ────────────────────
    # Declare parameters to enable Hypothesis-based fuzzing.
    # Omit it and the sweep step skips cleanly.

    # from qloop.core.spec import BitstringDomain, FloatDomain, IntDomain
    # def param_space(self) -> ParamSpace:
    #     return ParamSpace(
    #         marked=BitstringDomain(length=2),
    #         theta=FloatDomain(0.0, 3.14159),
    #     )
