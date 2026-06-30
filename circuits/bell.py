from qiskit import QuantumCircuit


def bell_circuit() -> QuantumCircuit:
    """Bell state |Φ+⟩ = (|00⟩ + |11⟩)/√2, no measurement."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc


def bell_circuit_measured() -> QuantumCircuit:
    """Bell state with measurement on both qubits for sampling tiers."""
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc
