"""
CircuitSpec — the contract every circuit plugin implements.

Supporting types:
  Invariant  — named boolean check (circuit, statevector) → bool
  Budget     — max depth / gate counts, with optional per-topology overrides
  ParamSpace — declared parameter domains for hypothesis fuzzing
  *Domain    — concrete domain types (bitstring, float, int)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, ClassVar

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

# ── Invariant ──────────────────────────────────────────────────────────────────

InvariantCheck = Callable[[QuantumCircuit, Statevector], bool]


@dataclass
class Invariant:
    """A named boolean property that must hold for a circuit's output state."""

    name: str
    check: InvariantCheck
    message: str


# ── Budget ─────────────────────────────────────────────────────────────────────


@dataclass
class Budget:
    """
    Resource limits for transpiled circuits.

    depth / two_qubit_gates: limits for ideal or all-to-all targets (no routing overhead).
    depth_limited / two_qubit_gates_limited: limits for sparse topologies (heavy-hex etc.)
    where SWAP insertion inflates depth.  If the *_limited fields are None, the default
    values are used for all targets.
    """

    depth: int = 200
    two_qubit_gates: int = 50
    depth_limited: int | None = None
    two_qubit_gates_limited: int | None = None

    def for_target(self, target: dict) -> dict:
        """Return {'depth': ..., 'two_qubit_gates': ...} appropriate for this target."""
        is_limited = target.get("coupling") == "heavy-hex"
        return {
            "depth": (
                self.depth_limited
                if is_limited and self.depth_limited is not None
                else self.depth
            ),
            "two_qubit_gates": (
                self.two_qubit_gates_limited
                if is_limited and self.two_qubit_gates_limited is not None
                else self.two_qubit_gates
            ),
        }


# ── ParamSpace ─────────────────────────────────────────────────────────────────


@dataclass
class _Domain:
    kind: str = field(init=False)


@dataclass
class BitstringDomain(_Domain):
    """A bitstring parameter of fixed length (e.g. Grover's marked state)."""

    length: int
    kind: str = field(default="bitstring", init=False)


@dataclass
class FloatDomain(_Domain):
    """A float parameter in [min_val, max_val]."""

    min_val: float
    max_val: float
    kind: str = field(default="float", init=False)


@dataclass
class IntDomain(_Domain):
    """An integer parameter in [min_val, max_val]."""

    min_val: int
    max_val: int
    kind: str = field(default="int", init=False)


class ParamSpace:
    """
    Declares the parameter space of a parameterized circuit.

    Used by the framework to generate Hypothesis strategies and drive fuzzing.
    """

    def __init__(self, **domains: _Domain) -> None:
        self.domains = domains

    @classmethod
    def empty(cls) -> ParamSpace:
        return cls()

    def is_empty(self) -> bool:
        return not self.domains


# ── CircuitSpec ────────────────────────────────────────────────────────────────


class CircuitSpec(ABC):
    """
    Contract for a Qloop circuit plugin.

    Minimum viable plugin — only build() + name/n_qubits are required.
    Every other declaration is optional; omitting it causes the corresponding
    pipeline stage to SKIP (with a visible reason), never to silently pass.

    Class attributes (required, must be set in the subclass body):
        name      unique identifier used in the registry and test parametrization
        n_qubits  qubit count returned by build() with default parameters
        tags      optional list of category labels for by_tag() queries
    """

    name: ClassVar[str]
    n_qubits: ClassVar[int]
    tags: ClassVar[list[str]] = []

    @abstractmethod
    def build(self, **params) -> QuantumCircuit:
        """Construct and return the circuit (no measurements)."""
        ...

    # ── Exact tier ─────────────────────────────────────────────────────────────

    def reference_state(self, **params) -> Statevector | None:
        """Known-good statevector, or None to skip the exact state comparison."""
        return None

    def reference_expectation(self, **params) -> float | None:
        """Known-good expectation value (e.g. ground state energy), or None to skip."""
        return None

    # ── Property tier ──────────────────────────────────────────────────────────

    def invariants(self) -> list[Invariant]:
        """Return parameter-independent invariants. Normalization is added automatically."""
        return []

    def invariants_for(self, **params) -> list[Invariant]:
        """
        Return invariants given specific parameter values.

        Default: delegates to invariants().  Override for param-dependent checks
        (e.g. Grover's marked-state dominance depends on which state is marked).
        """
        return self.invariants()

    # ── Transpile tier ─────────────────────────────────────────────────────────

    def budget(self) -> Budget:
        """Resource budget for the transpilation build check."""
        return Budget()

    # ── Noisy tier ─────────────────────────────────────────────────────────────

    def expected_distribution(self, **params) -> dict[str, float] | None:
        """
        Ideal output probability distribution, or None to skip noisy assertions.

        Keys are bitstrings (e.g. '00', '11'); values are probabilities in [0, 1].
        The noisy test asserts each outcome falls within a tolerance band.
        """
        return None

    # ── Param sweep ────────────────────────────────────────────────────────────

    def param_space(self) -> ParamSpace:
        """Declare parameters for hypothesis-based fuzzing. Empty → skip fuzzing."""
        return ParamSpace.empty()
