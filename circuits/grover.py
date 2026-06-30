from qiskit import QuantumCircuit


def _oracle(qc: QuantumCircuit, marked: str) -> None:
    """Phase-flip oracle: flips sign of |marked⟩."""
    n = len(marked)
    # Flip qubits where the marked bit is '0' (LSB = qubit 0)
    for i, bit in enumerate(reversed(marked)):
        if bit == "0":
            qc.x(i)
    # Multi-controlled Z via CX + H trick
    if n == 2:
        qc.h(1)
        qc.cx(0, 1)
        qc.h(1)
    elif n == 3:
        qc.h(2)
        qc.ccx(0, 1, 2)
        qc.h(2)
    # Unflip
    for i, bit in enumerate(reversed(marked)):
        if bit == "0":
            qc.x(i)


def _diffuser(qc: QuantumCircuit, n: int) -> None:
    """Grover diffusion operator (inversion about average)."""
    qc.h(range(n))
    qc.x(range(n))
    if n == 2:
        qc.h(1)
        qc.cx(0, 1)
        qc.h(1)
    elif n == 3:
        qc.h(2)
        qc.ccx(0, 1, 2)
        qc.h(2)
    qc.x(range(n))
    qc.h(range(n))


def grover_circuit(marked: str) -> QuantumCircuit:
    """
    Grover search circuit for a 2- or 3-qubit marked bitstring.

    Args:
        marked: Target bitstring, e.g. '10' or '101'. Length determines qubit count.

    Returns:
        QuantumCircuit with one Grover iteration (no measurement).
    """
    n = len(marked)
    if n not in (2, 3):
        raise ValueError(f"marked must be 2 or 3 bits, got {n}")

    qc = QuantumCircuit(n)
    qc.h(range(n))        # uniform superposition
    _oracle(qc, marked)   # phase kick
    _diffuser(qc, n)      # amplitude amplification
    return qc
