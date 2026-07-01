"""Transpilation pipeline: compile circuits per target and assert they fit budgets."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import QuantumRegister
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary as _SEL
from qiskit.circuit.library import HGate, XGate
from qiskit.transpiler import CouplingMap


def _register_ry_rz_equivalences() -> None:
    """
    Register H→RY+RZ and X→RZ+RY equivalences in Qiskit's SessionEquivalenceLibrary.

    Qiskit 2.x's BasisTranslator does not include these rules by default, so
    transpiling to a {cx, ry, rz} basis (e.g. the all-to-all trapped-ion target)
    fails unless we add them. Called once at module import.
    """
    q = QuantumRegister(1, "q")

    # H = RY(π/2)·RZ(π) (up to global phase −i, which is phase-insensitive here)
    h_def = QuantumCircuit(q)
    h_def.ry(np.pi / 2, 0)
    h_def.rz(np.pi, 0)
    _SEL.add_equivalence(HGate(), h_def)

    # X = RZ(π)·RY(π) (up to global phase i)
    x_def = QuantumCircuit(q)
    x_def.rz(np.pi, 0)
    x_def.ry(np.pi, 0)
    _SEL.add_equivalence(XGate(), x_def)


_register_ry_rz_equivalences()


@dataclass
class TranspileMetrics:
    depth: int
    gate_counts: dict[str, int]
    two_qubit_gate_count: int
    mapped_successfully: bool


_TWO_QUBIT_GATES = {"cx", "cz", "rxx", "rzz", "ecr", "swap", "iswap", "dcx"}


def transpile_for_target(
    circuit: QuantumCircuit,
    target: dict,
    coupling_map: CouplingMap | None = None,
) -> tuple[QuantumCircuit, TranspileMetrics]:
    """
    Transpile a circuit to fit a specific backend target.

    Args:
        circuit: Source QuantumCircuit (may include measurements).
        target: Parsed target dict from targets.yaml.
        coupling_map: Optional CouplingMap; pass coupling_map_for(target) for noisy targets.

    Returns:
        (transpiled_circuit, TranspileMetrics)
    """
    basis_gates = target.get("basis_gates")
    optimization_level = 2

    try:
        transpiled = transpile(
            circuit,
            basis_gates=basis_gates,
            coupling_map=coupling_map,
            optimization_level=optimization_level,
            seed_transpiler=42,
        )
        mapped_successfully = True
    except Exception:
        transpiled = circuit
        mapped_successfully = False

    ops = transpiled.count_ops()
    gate_counts = dict(ops)
    two_qubit_count = sum(v for k, v in gate_counts.items() if k in _TWO_QUBIT_GATES)

    metrics = TranspileMetrics(
        depth=transpiled.depth(),
        gate_counts=gate_counts,
        two_qubit_gate_count=two_qubit_count,
        mapped_successfully=mapped_successfully,
    )
    return transpiled, metrics


class BudgetExceeded(Exception):
    pass


def assert_fits(metrics: TranspileMetrics, budget: dict) -> None:
    """
    Assert the transpiled circuit fits within the configured budget.

    Args:
        metrics: TranspileMetrics returned by transpile_for_target.
        budget: Dict with optional keys 'depth' and 'two_qubit_gates'.

    Raises:
        BudgetExceeded: If depth or gate count exceeds the budget.
    """
    if not metrics.mapped_successfully:
        raise BudgetExceeded("Transpilation failed — circuit could not be mapped to target")

    if "depth" in budget and metrics.depth > budget["depth"]:
        raise BudgetExceeded(
            f"Depth {metrics.depth} exceeds budget {budget['depth']}"
        )

    if "two_qubit_gates" in budget and metrics.two_qubit_gate_count > budget["two_qubit_gates"]:
        raise BudgetExceeded(
            f"Two-qubit gate count {metrics.two_qubit_gate_count} "
            f"exceeds budget {budget['two_qubit_gates']}"
        )
