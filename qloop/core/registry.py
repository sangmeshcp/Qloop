"""
Circuit plugin registry with filesystem auto-discovery.

Usage:
    from qloop.core.registry import registry

    for spec in registry.all():           # iterate all plugins
        print(spec.name, spec.tags)

    spec = registry.get("bell")           # lookup by name
    clifford = registry.by_tag("clifford")  # filter by tag

Discovery:
    When registry.all() / registry.get() is first called, the registry scans
    qloop/circuits/ for modules, imports each one, and registers every
    concrete CircuitSpec subclass whose __module__ starts with "qloop.circuits.".
    No manual registration list is needed — drop a file in, it's discovered.

Validation at registration:
    - name must be a non-empty string
    - n_qubits must be a positive integer
    - build() must return a QuantumCircuit
    - Duplicate names raise ValueError immediately
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Iterator

from qiskit import QuantumCircuit

from qloop.core.spec import CircuitSpec


class _Registry:
    def __init__(self) -> None:
        self._specs: dict[str, CircuitSpec] = {}
        self._discovered = False

    # ── Public API ─────────────────────────────────────────────────────────────

    def register(self, spec: CircuitSpec) -> None:
        """Manually register a spec. Raises ValueError on duplicate name."""
        self._validate(spec)
        if spec.name in self._specs:
            raise ValueError(
                f"Duplicate circuit name: '{spec.name}'. "
                f"Already registered by {type(self._specs[spec.name]).__name__}."
            )
        self._specs[spec.name] = spec

    def get(self, name: str) -> CircuitSpec:
        """Return a spec by name; raises KeyError if not found."""
        self._ensure_discovered()
        return self._specs[name]

    def all(self) -> list[CircuitSpec]:
        """Return all registered specs in stable alphabetical order."""
        self._ensure_discovered()
        return sorted(self._specs.values(), key=lambda s: s.name)

    def by_tag(self, tag: str) -> list[CircuitSpec]:
        """Return all specs that carry the given tag."""
        self._ensure_discovered()
        return [s for s in self.all() if tag in s.tags]

    # ── Discovery ──────────────────────────────────────────────────────────────

    def _ensure_discovered(self) -> None:
        if not self._discovered:
            self._discover()
            self._discovered = True

    def _discover(self) -> None:
        """
        Import every module under qloop.circuits and register concrete specs.

        Only classes whose __module__ starts with 'qloop.circuits.' are registered
        so that test-helper subclasses defined elsewhere never leak in.
        """
        pkg = importlib.import_module("qloop.circuits")
        for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
            importlib.import_module(f"qloop.circuits.{module_name}")

        seen: set[type] = set()
        for subclass in _all_subclasses(CircuitSpec):
            if subclass in seen:
                continue
            seen.add(subclass)

            if not getattr(subclass, "__module__", "").startswith("qloop.circuits."):
                continue
            if subclass.__abstractmethods__:
                continue
            if not hasattr(subclass, "name") or not hasattr(subclass, "n_qubits"):
                continue

            try:
                instance = subclass()
                self.register(instance)
            except ValueError:
                raise  # duplicate name — propagate loudly
            except Exception as exc:
                import warnings
                warnings.warn(
                    f"Could not register {subclass.__name__}: {exc}", stacklevel=2
                )

    # ── Validation ─────────────────────────────────────────────────────────────

    @staticmethod
    def _validate(spec: CircuitSpec) -> None:
        """Validate a spec at registration time; raise ValueError if invalid."""
        name = getattr(spec, "name", None)
        if not name or not isinstance(name, str):
            raise ValueError(
                f"{type(spec).__name__}: 'name' must be a non-empty string, got {name!r}"
            )
        n = getattr(spec, "n_qubits", None)
        if not isinstance(n, int) or n <= 0:
            raise ValueError(
                f"'{name}': 'n_qubits' must be a positive int, got {n!r}"
            )
        try:
            circuit = spec.build()
        except Exception as exc:
            raise ValueError(f"'{name}': build() raised {type(exc).__name__}: {exc}") from exc
        if not isinstance(circuit, QuantumCircuit):
            raise ValueError(f"'{name}': build() must return QuantumCircuit, got {type(circuit)}")


def _all_subclasses(cls: type) -> Iterator[type]:
    for sub in cls.__subclasses__():
        yield sub
        yield from _all_subclasses(sub)


# Module-level singleton — import this everywhere
registry = _Registry()
