"""
Quantum Volume: the canonical noisy-tier statistical benchmark.

Source: Cross, Bishop, Sheldon, Nation, Gambetta, "Validating quantum
computers using randomized model circuits," Phys. Rev. A 100, 032328
(2019). n layers of: a random qubit permutation, then a Haar-random U(4)
unitary applied to each adjacent pair under that permutation. Success
criterion: the ideal (noiseless) output distribution's "heavy" outcomes
(those with probability above the median across all 2^n bitstrings) carry
more than 2/3 of the total probability mass — a property of genuinely
random circuits, not a closed-form target this plugin could check against
an external reference. The oracle here is therefore the heavy-output
statistical property itself (see heavy_output_probability_exceeds in
qloop/core/invariants.py), computed directly from the circuit's own ideal
statevector — the same self-contained pattern as the unitary() invariant,
not a two-independent-computations cross-check.

Differential-test note: Qiskit ships qiskit.circuit.library.QuantumVolume,
which this plugin does not use, to keep the construction (and its fixed
seed, needed for reproducible exact-tier assertions) fully transparent and
locally auditable rather than depending on library internals that may
change the random-number consumption order across Qiskit versions.

Reproducibility: the "random" unitaries are generated from a fixed seed
(0), chosen after checking (see git history) that it comfortably clears the
2/3 threshold (measured: 0.889) rather than sitting near the boundary where
floating-point differences across environments could flip the invariant.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from scipy.stats import unitary_group

from qloop.core.invariants import heavy_output_probability_exceeds, normalized, unitary
from qloop.core.spec import Budget, CircuitSpec

N = 4
SEED = 0
HEAVY_THRESHOLD = 2.0 / 3.0


def quantum_volume_circuit(n: int = N, seed: int = SEED) -> QuantumCircuit:
    """n layers of (random permutation, random U(4) per adjacent pair)."""
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    for layer in range(n):
        perm = rng.permutation(n)
        pairs = [(perm[i], perm[i + 1]) for i in range(0, n - n % 2, 2)]
        for a, b in pairs:
            u = unitary_group.rvs(4, random_state=rng)
            qc.unitary(u, [int(a), int(b)], label=f"SU4_L{layer}")
    return qc


def heavy_outputs(n: int = N, seed: int = SEED, top: int = 4) -> dict[str, float]:
    """Exact ideal probabilities of the `top` highest-probability heavy outcomes."""
    from qiskit.quantum_info import Statevector

    sv = Statevector(quantum_volume_circuit(n, seed))
    probs = sv.probabilities()
    median = np.median(probs)
    heavy_idx = [i for i in range(len(probs)) if probs[i] > median]
    heavy_idx.sort(key=lambda i: probs[i], reverse=True)
    return {format(i, f"0{n}b"): float(probs[i]) for i in heavy_idx[:top]}


class QuantumVolumeSpec(CircuitSpec):
    """Quantum Volume model circuit (fixed seed): heavy-output probability > 2/3."""

    name = "quantum-volume"
    n_qubits = N
    tags = ["benchmark", "noisy-tier-anchor"]

    def build(self, **params) -> QuantumCircuit:
        return quantum_volume_circuit(N, SEED)

    def invariants(self):
        return [normalized(), unitary(), heavy_output_probability_exceeds(HEAVY_THRESHOLD)]

    def budget(self) -> Budget:
        # Measured: sim-ideal depth=4 (UnitaryGate left opaque, no basis
        # constraint); sim-noisy-alltoall depth~39/18 2q; sim-noisy-heavyhex
        # depth~54/24 2q (random SU(4) requires routing regardless of
        # topology since the permutation is itself random per layer).
        return Budget(depth=60, two_qubit_gates=25, depth_limited=80, two_qubit_gates_limited=35)

    def expected_distribution(self, **params) -> dict[str, float]:
        # Proxy for the true QV criterion (aggregate heavy-output mass under
        # noise): the framework's noisy tier checks individual bitstring
        # probabilities against a tolerance band, not an aggregate, so this
        # reports the top 4 heavy outcomes' exact ideal probabilities and
        # relies on each holding up individually under noise. The literal
        # QV success criterion (ideal aggregate heavy-output mass > 2/3) is
        # checked exactly in invariants(), not here.
        return heavy_outputs(N, SEED, top=4)

    # No param_space: this circuit's identity IS its fixed seed — sweeping
    # it would defeat the reproducibility the exact-tier invariant depends on.
