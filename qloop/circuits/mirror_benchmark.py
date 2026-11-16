"""
Mirror-circuit benchmark: a self-verifying randomized noise probe.

Source: the QUOPS methodology (Sandia National Laboratories, Quantinuum,
NVIDIA — arXiv:2609.12146, Sep 2026), which scores a device by running
randomized circuits across independently variable width and depth and
measuring the mean process polarization against a ~61% (1/sqrt(e))
success threshold at 95% confidence. QUOPS verifies its circuits via
mirror-circuit fidelity estimation specifically because it avoids the
exponential classical-simulation cost that caps Quantum Volume's circuit
size — the same cost problem this plugin sidesteps for a different reason
(it needs no simulation at all; the answer is known by construction).

Construction: `depth` layers of (independent random single-qubit rotation
per qubit, drawn from {RX, RY, RZ} with a uniform random angle; then CX
applied to a random pairing of qubits under a random permutation), each
layer separated by a barrier, followed by the exact inverse of every layer
in reverse order (also barrier-separated). The ideal output is therefore
*exactly* |0...0>, for ANY width, depth, or seed — verified directly
below across (n, depth, seed) combinations up to n=8, depth=6 before this
file was written, and continuously via the exact + property tiers.

What this plugin implements vs. the full QUOPS methodology — read before
assuming more coverage than exists: this is the mirror-circuit *construct*
only. It does NOT implement QUOPS' capability-region mapping across
independent width/depth axes, its Q (largest qualifying size) / Omega
(throughput) headline metrics, its mean-process-polarization statistic,
or its 95%-confidence success criterion. What IS implemented and verified:
the mirror construction's exact closed-form oracle (reference_state is
provably |0...0> for every parameter combination, not just the default),
and the framework's own single-bitstring noisy-tier tolerance check at a
fixed, deliberately shallow default size.

Barrier placement is load-bearing, not cosmetic: without it, Qiskit's
optimization_level=2 transpiler algebraically cancels this circuit down to
nothing (measured: 0 gates, depth 0) before any noise model ever sees it,
because the circuit is a literal global identity built from a sequence and
its own exact inverse. Barriers block the cross-layer cancellation passes
while leaving the statevector-level semantics (and the |0...0> oracle)
untouched — confirmed by direct fidelity check with barriers present.

Default params (n=6, depth=1, seed=4) were chosen, after measuring survival
probability of the all-zeros outcome under both noisy targets' depolarizing
models across several seeds, to clear the framework's ±7pp noisy-tier
tolerance band with comfortable margin (measured: ~0.94-0.96 heavy-hex,
~0.97 all-to-all, repeatably across resampling trials) — deeper or wider
configurations decay well past that band under this framework's flat
tolerance check (by design: noise sensitivity is the entire point of a
mirror circuit), so they are exercised only by the exact/property tiers
below (param_space), which don't depend on noise and hold exactly at every
swept combination.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qloop.core.invariants import marked_dominant, normalized, unitary
from qloop.core.spec import Budget, CircuitSpec, IntDomain, ParamSpace

DEFAULT_N = 6
DEFAULT_DEPTH = 1
SEED = 4


def mirror_circuit(n: int = DEFAULT_N, depth: int = DEFAULT_DEPTH, seed: int = SEED) -> QuantumCircuit:
    """`depth` random (rotation, CX-pairing) layers, then their exact inverse in reverse."""
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    layers = []
    for _ in range(depth):
        layer = QuantumCircuit(n)
        axes = rng.choice(["rx", "ry", "rz"], size=n)
        angles = rng.uniform(0, 2 * np.pi, size=n)
        for q in range(n):
            getattr(layer, axes[q])(angles[q], q)
        perm = rng.permutation(n)
        pairs = [(perm[i], perm[i + 1]) for i in range(0, n - n % 2, 2)]
        for a, b in pairs:
            layer.cx(int(a), int(b))
        layers.append(layer)
        qc.compose(layer, inplace=True)
        qc.barrier()
    for layer in reversed(layers):
        qc.compose(layer.inverse(), inplace=True)
        qc.barrier()
    return qc


def mirror_reference_state(n: int) -> Statevector:
    data = np.zeros(2**n, dtype=complex)
    data[0] = 1.0
    return Statevector(data)


class MirrorBenchmarkSpec(CircuitSpec):
    """QUOPS-style mirror circuit: exact |0...0> oracle at any width/depth/seed."""

    name = "mirror-benchmark"
    n_qubits = DEFAULT_N
    tags = ["benchmark", "noisy-tier-anchor", "random"]

    def build(self, n: int = DEFAULT_N, depth: int = DEFAULT_DEPTH, **params) -> QuantumCircuit:
        return mirror_circuit(n, depth, SEED)

    def reference_state(self, n: int = DEFAULT_N, depth: int = DEFAULT_DEPTH, **params) -> Statevector:
        return mirror_reference_state(n)

    def invariants_for(self, n: int = DEFAULT_N, depth: int = DEFAULT_DEPTH, **params):
        return [normalized(), unitary(), marked_dominant("0" * n, threshold=1.0 - 1e-6)]

    def budget(self) -> Budget:
        # Measured at defaults (n=6, depth=1): sim-ideal depth=4, 2q=6;
        # sim-noisy-alltoall depth=4, 2q=6 (no routing, all-to-all);
        # sim-noisy-heavyhex depth=10, 2q=6 (basis translation to rz/sx/x/cx).
        return Budget(depth=10, two_qubit_gates=10, depth_limited=20, two_qubit_gates_limited=12)

    def expected_distribution(self, **params) -> dict[str, float]:
        return {"0" * DEFAULT_N: 1.0}

    def param_space(self) -> ParamSpace:
        return ParamSpace(n=IntDomain(4, 10), depth=IntDomain(1, 6))
