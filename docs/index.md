# Qloop

A quantum-circuit SDLC framework built on classical simulators: a plugin registry that auto-discovers circuits, six pipeline stages (lint → exact → property → transpile → noisy → hardware), and a 17-circuit corpus that exercises every stage.

If you've never seen this repo before, read these in order:

1. **[Architecture](architecture.html)** — how the pieces fit together: the `CircuitSpec` contract, the registry, the six stages, and where Stim fits in.
2. **[Installation](installation.html)** — get a working environment.
3. **[Usage](usage.html)** — run the pipeline, run one stage, read the metrics artifact.
4. **[Testing](testing.html)** — how the test suite is organized, and how to debug one circuit.
5. **[Adding a circuit](adding-a-circuit.html)** — the only page you need to contribute a new circuit.
6. **[Extending the framework](extending.html)** — changes that go deeper than "add a circuit": new invariants, new backends, new contract methods.
7. **[Circuit corpus](circuit-corpus.html)** — reference table of all 17 registered circuits.

## The one-sentence pitch

Drop a single Python file implementing a small contract (`CircuitSpec`) into `qloop/circuits/`, and it is automatically picked up by every test tier — exact verification, property-based invariants, a transpilation budget check across multiple hardware topologies, and (optionally) noisy-simulation tolerance bands — with **zero edits** to the test suite, CI config, or any registration list.

```python
# qloop/circuits/my_circuit.py
from qiskit import QuantumCircuit
from qloop.core.spec import CircuitSpec, Budget

class MyCircuitSpec(CircuitSpec):
    name = "my-circuit"
    n_qubits = 2

    def build(self, **params) -> QuantumCircuit:
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        return qc

    def budget(self) -> Budget:
        return Budget(depth=10, two_qubit_gates=5)
```

```bash
pytest tests/generic/ -v -k my-circuit
```

That's it — no import list, no CI edit, no test file to write. See [Adding a circuit](adding-a-circuit.html) for the full contract, including which optional methods unlock which pipeline stages.

## Source

[github.com/sangmeshcp/Qloop](https://github.com/sangmeshcp/Qloop)
