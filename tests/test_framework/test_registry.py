"""
Registry unit tests: discovery, deduplication, tag filtering, and lookup.

These tests verify the plugin registry itself — not the circuits it contains.
"""

from __future__ import annotations

import pytest
from qiskit import QuantumCircuit

from qloop.core.registry import _Registry
from qloop.core.spec import CircuitSpec


class _FakeSpec(CircuitSpec):
    name = "fake-registry-test"
    n_qubits = 1
    tags = ["test", "clifford"]

    def build(self, **params) -> QuantumCircuit:
        qc = QuantumCircuit(1)
        qc.h(0)
        return qc


class _AnotherSpec(CircuitSpec):
    name = "another-registry-test"
    n_qubits = 2
    tags = ["test"]

    def build(self, **params) -> QuantumCircuit:
        return QuantumCircuit(2)


def _fresh_registry(*specs) -> _Registry:
    r = _Registry()
    r._discovered = True  # skip auto-discovery; we control population
    for s in specs:
        r.register(s)
    return r


# ── Discovery ──────────────────────────────────────────────────────────────────


def test_discovery_finds_all_builtin_specs():
    """Auto-discovery should load all four built-in circuit plugins."""
    from qloop.core.registry import registry

    names = {s.name for s in registry.all()}
    assert {"bell", "grover", "vqe", "ghz"} <= names, (
        f"Missing circuits. Found: {names}"
    )


def test_all_returns_stable_alphabetical_order():
    from qloop.core.registry import registry

    names = [s.name for s in registry.all()]
    assert names == sorted(names)


# ── Registration ───────────────────────────────────────────────────────────────


def test_register_and_get():
    r = _fresh_registry(_FakeSpec())
    spec = r.get("fake-registry-test")
    assert spec.name == "fake-registry-test"
    assert spec.n_qubits == 1


def test_get_missing_raises_key_error():
    r = _fresh_registry(_FakeSpec())
    with pytest.raises(KeyError):
        r.get("does-not-exist")


def test_duplicate_name_raises_value_error():
    r = _fresh_registry(_FakeSpec())
    with pytest.raises(ValueError, match="Duplicate circuit name"):
        r.register(_FakeSpec())  # second registration of same name


# ── Validation ─────────────────────────────────────────────────────────────────


def test_empty_name_raises():
    class _Bad(CircuitSpec):
        name = ""
        n_qubits = 1

        def build(self, **params):
            return QuantumCircuit(1)

    r = _fresh_registry()
    with pytest.raises(ValueError, match="name"):
        r.register(_Bad())


def test_zero_qubits_raises():
    class _Bad(CircuitSpec):
        name = "bad-zero-qubits"
        n_qubits = 0

        def build(self, **params):
            return QuantumCircuit(1)

    r = _fresh_registry()
    with pytest.raises(ValueError, match="n_qubits"):
        r.register(_Bad())


def test_build_not_returning_circuit_raises():
    class _Bad(CircuitSpec):
        name = "bad-build-return"
        n_qubits = 1

        def build(self, **params):
            return "not a circuit"

    r = _fresh_registry()
    with pytest.raises(ValueError, match="build\\(\\)"):
        r.register(_Bad())


# ── Tag filtering ──────────────────────────────────────────────────────────────


def test_by_tag_returns_matching_specs():
    r = _fresh_registry(_FakeSpec(), _AnotherSpec())
    clifford = r.by_tag("clifford")
    assert len(clifford) == 1
    assert clifford[0].name == "fake-registry-test"


def test_by_tag_returns_empty_for_unknown_tag():
    r = _fresh_registry(_FakeSpec())
    assert r.by_tag("nonexistent-tag") == []


def test_by_tag_on_auto_registry_clifford():
    from qloop.core.registry import registry

    clifford = registry.by_tag("clifford")
    names = {s.name for s in clifford}
    assert "bell" in names
    assert "ghz" in names
