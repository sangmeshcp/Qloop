"""Build Aer noise models and coupling maps from targets.yaml entries."""

from __future__ import annotations

from qiskit.transpiler import CouplingMap
from qiskit_aer.noise import NoiseModel, depolarizing_error

# Small fixed coupling maps for superconducting topologies.
# 5-qubit heavy-hex approximation (linear chain mimicking heavy-hex connectivity).
_HEAVY_HEX_EDGES = [(0, 1), (1, 2), (2, 3), (3, 4)]

# All-to-all for up to 4 qubits (trapped-ion-like).
_ALL_TO_ALL_EDGES = [(i, j) for i in range(4) for j in range(4) if i != j]


def coupling_map_for(target: dict) -> CouplingMap | None:
    """
    Return a CouplingMap for the named topology, or None for all-to-all.

    For all-to-all (trapped-ion-like), we return a concrete 4-qubit fully
    connected map rather than None.  Qiskit 2.x's transpiler can behave
    unpredictably when coupling_map=None; an explicit dense map ensures correct
    routing-pass behaviour while preserving the "no SWAP overhead" property.

    Args:
        target: Parsed target dict from targets.yaml.

    Returns:
        CouplingMap instance for both heavy-hex and all-to-all topologies.
    """
    coupling = target.get("coupling", "")
    if coupling == "heavy-hex":
        return CouplingMap(_HEAVY_HEX_EDGES)
    # all-to-all: explicit 4-qubit fully-connected map
    return CouplingMap(_ALL_TO_ALL_EDGES)


def build_noise_model(target: dict) -> NoiseModel:
    """
    Build an Aer NoiseModel from depolarizing parameters in the target dict.

    1q error is applied to all single-qubit basis gates.
    2q error is applied to all two-qubit basis gates.

    Args:
        target: Parsed target dict from targets.yaml with keys
                'basis_gates', 'depolarizing_1q', 'depolarizing_2q'.

    Returns:
        Configured NoiseModel.
    """
    p1 = target["depolarizing_1q"]
    p2 = target["depolarizing_2q"]
    basis_gates = target["basis_gates"]

    noise_model = NoiseModel()

    single_qubit_gates = [g for g in basis_gates if g not in ("cx", "cz", "rxx", "rzz", "ecr")]
    two_qubit_gates = [g for g in basis_gates if g in ("cx", "cz", "rxx", "rzz", "ecr")]

    if single_qubit_gates:
        error_1q = depolarizing_error(p1, 1)
        noise_model.add_all_qubit_quantum_error(error_1q, single_qubit_gates)

    if two_qubit_gates:
        error_2q = depolarizing_error(p2, 2)
        noise_model.add_all_qubit_quantum_error(error_2q, two_qubit_gates)

    return noise_model
