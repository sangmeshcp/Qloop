"""
Contract tests: every registered CircuitSpec satisfies the plugin contract.

Parametrized over registry.all() so each new circuit plugin gets these checks
automatically without any edits here.
"""

from __future__ import annotations

import pytest
from qiskit import QuantumCircuit

from qloop.core.registry import registry
from qloop.core.spec import Budget, CircuitSpec, ParamSpace

_ALL_SPECS = registry.all()


@pytest.mark.parametrize("spec", _ALL_SPECS, ids=[s.name for s in _ALL_SPECS])
class TestCircuitContract:
    def test_name_is_nonempty_string(self, spec: CircuitSpec):
        assert isinstance(spec.name, str) and spec.name, (
            f"{type(spec).__name__}.name must be a non-empty string"
        )

    def test_n_qubits_is_positive_int(self, spec: CircuitSpec):
        assert isinstance(spec.n_qubits, int) and spec.n_qubits > 0, (
            f"{type(spec).__name__}.n_qubits must be a positive int"
        )

    def test_tags_is_list_of_strings(self, spec: CircuitSpec):
        assert isinstance(spec.tags, list), f"{spec.name}: tags must be a list"
        assert all(isinstance(t, str) for t in spec.tags), (
            f"{spec.name}: all tags must be strings"
        )

    def test_build_returns_quantum_circuit(self, spec: CircuitSpec):
        qc = spec.build()
        assert isinstance(qc, QuantumCircuit), (
            f"{spec.name}: build() must return QuantumCircuit, got {type(qc)}"
        )

    def test_build_qubit_count_matches_n_qubits(self, spec: CircuitSpec):
        qc = spec.build()
        assert qc.num_qubits == spec.n_qubits, (
            f"{spec.name}: build() returned {qc.num_qubits} qubits, "
            f"expected n_qubits={spec.n_qubits}"
        )

    def test_budget_returns_budget(self, spec: CircuitSpec):
        b = spec.budget()
        assert isinstance(b, Budget), (
            f"{spec.name}: budget() must return Budget, got {type(b)}"
        )

    def test_budget_positive_values(self, spec: CircuitSpec):
        b = spec.budget()
        assert b.depth > 0, f"{spec.name}: budget.depth must be positive"
        assert b.two_qubit_gates > 0, f"{spec.name}: budget.two_qubit_gates must be positive"

    def test_param_space_returns_param_space(self, spec: CircuitSpec):
        ps = spec.param_space()
        assert isinstance(ps, ParamSpace), (
            f"{spec.name}: param_space() must return ParamSpace, got {type(ps)}"
        )

    def test_invariants_returns_list(self, spec: CircuitSpec):
        inv = spec.invariants()
        assert isinstance(inv, list), f"{spec.name}: invariants() must return a list"

    def test_reference_state_is_none_or_statevector(self, spec: CircuitSpec):
        from qiskit.quantum_info import Statevector

        rs = spec.reference_state()
        assert rs is None or isinstance(rs, Statevector), (
            f"{spec.name}: reference_state() must return Statevector or None"
        )

    def test_expected_distribution_is_none_or_dict(self, spec: CircuitSpec):
        ed = spec.expected_distribution()
        assert ed is None or isinstance(ed, dict), (
            f"{spec.name}: expected_distribution() must return dict or None"
        )
        if isinstance(ed, dict):
            assert all(isinstance(k, str) for k in ed), (
                f"{spec.name}: expected_distribution keys must be bitstrings"
            )
            assert all(0.0 <= v <= 1.0 for v in ed.values()), (
                f"{spec.name}: expected_distribution values must be probabilities"
            )

    def test_stim_param_space_returns_param_space(self, spec: CircuitSpec):
        ps = spec.stim_param_space()
        assert isinstance(ps, ParamSpace), (
            f"{spec.name}: stim_param_space() must return ParamSpace, got {type(ps)}"
        )

    def test_stim_program_is_none_or_stim_circuit(self, spec: CircuitSpec):
        import stim

        ps = spec.stim_param_space()
        prog = spec.stim_program() if ps.is_empty() else None
        if ps.is_empty():
            assert prog is None or isinstance(prog, stim.Circuit), (
                f"{spec.name}: stim_program() must return stim.Circuit or None"
            )

    def test_large_circuit_declares_stim_or_skips_statevector(self, spec: CircuitSpec):
        """Circuits too large for Statevector must offer a Stim path (or decline both)."""
        from qloop.core.spec import MAX_STATEVECTOR_QUBITS

        if spec.n_qubits > MAX_STATEVECTOR_QUBITS:
            assert spec.reference_state() is None, (
                f"{spec.name}: n_qubits={spec.n_qubits} is too large for "
                "Statevector; reference_state() must return None"
            )
            assert spec.expected_distribution() is None, (
                f"{spec.name}: n_qubits={spec.n_qubits} is too large for "
                "Statevector/Aer sampling; expected_distribution() must return None"
            )
