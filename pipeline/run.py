"""
Simulation and hardware submission helpers.

Three tiers:
  run_ideal      — exact statevector (no noise, no shots)
  run_sampled    — Aer shot-based sampling, optionally noisy
  submit_hardware — stubbed; documents the async submit→poll→retrieve shape
"""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.transpiler import CouplingMap
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel


def run_ideal(circuit: QuantumCircuit) -> Statevector:
    """
    Run circuit on the exact statevector simulator.

    The circuit must NOT contain measurements — statevector simulation
    operates on pure quantum states.

    Args:
        circuit: QuantumCircuit without measurement operations.

    Returns:
        Statevector of the output state.
    """
    return Statevector(circuit)


def run_sampled(
    circuit: QuantumCircuit,
    shots: int,
    noise_model: NoiseModel | None = None,
    coupling_map: CouplingMap | None = None,
) -> dict[str, int]:
    """
    Run circuit with Aer shot-based sampling, optionally with noise.

    The circuit must contain measurement operations.

    Args:
        circuit: QuantumCircuit with measurements.
        shots: Number of shots.
        noise_model: Optional Aer NoiseModel for noisy simulation.
        coupling_map: Optional CouplingMap to enforce connectivity.

    Returns:
        dict mapping bitstring → count.
    """
    backend = AerSimulator(noise_model=noise_model, coupling_map=coupling_map)
    job = backend.run(circuit, shots=shots)
    result = job.result()
    return dict(result.get_counts())


def submit_hardware(circuit: QuantumCircuit, target: dict) -> None:
    """
    Hardware submission stub — not yet implemented.

    Extension point for real-backend execution. The async shape to implement:

        1. SUBMIT  — serialize circuit to OpenQASM / Qiskit IR and POST to
                     provider API (IBM Quantum / Amazon Braket / IonQ etc.).
                     Store the returned job_id for polling.

        2. POLL    — GET job status on an exponential-backoff schedule until
                     status ∈ {COMPLETED, FAILED, CANCELLED}. Respect provider
                     rate limits. Surface queue position / estimated wait.

        3. RETRIEVE — fetch result payload (counts / statevector if available),
                      decode into standard dict[str, int] format, and return.

    Recommended libraries:
        IBM:    qiskit-ibm-runtime (IBMRuntimeService, SamplerV2)
        Braket: amazon-braket-sdk (AwsDevice, LocalSimulator as dry-run)
        IonQ:   qiskit-ionq

    Args:
        circuit: Transpiled QuantumCircuit ready for hardware.
        target: Target dict from targets.yaml (name, topology, basis_gates).

    Raises:
        NotImplementedError: Always. Wire up a real provider above this line.
    """
    raise NotImplementedError(
        "hardware tier: wire up Braket/IBM async submit→poll→retrieve here. "
        f"Target: {target.get('name', 'unknown')}. "
        "See docstring for the expected async shape."
    )
