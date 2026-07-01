# Usage

## Running everything

```bash
pytest
```

Runs all six stages (1 is separate — run `ruff check .`) across every registered circuit and every backend target, plus the original hand-written seed-circuit tests.

## Running one stage

```bash
ruff check .                                                          # Stage 1
pytest tests/test_exact/ tests/generic/test_exact_all.py              # Stage 2
pytest tests/test_properties/ tests/generic/test_properties_all.py    # Stage 3
pytest tests/generic/test_stim_all.py                                 # Stage 3b (Clifford/Stim)
pytest tests/test_transpile/ tests/generic/test_transpile_all.py -s   # Stage 4 (-s prints metrics)
pytest tests/test_noisy/ tests/generic/test_noisy_all.py              # Stage 5
```

Stage 6 (hardware) isn't run via pytest directly — it's a CI-only nightly job that calls `submit_hardware()` for every target and checks it correctly raises `NotImplementedError` (see `.github/workflows/ci.yml`).

## Running one circuit

Every generic test is parametrized with an ID matching the circuit's `name` (and, for stage 4/5, the target name too):

```bash
pytest tests/generic/ -v -k "qaoa-maxcut"
pytest tests/generic/test_transpile_all.py -v -s -k "bb-code-72 and heavyhex"
```

## Reading `metrics.json`

Every Stage 4 run records `{circuit, target, stage, depth, two_qubit_gates, mapped}` for each `(circuit, target)` pair via `qloop/pipeline/report.py`'s `MetricsCollector`. The root `conftest.py` flushes it to `metrics.json` at the end of the pytest session:

```bash
pytest tests/generic/test_transpile_all.py
python3 -c "
import json
data = json.load(open('metrics.json'))['entries']
for e in data:
    if e['circuit'] == 'bb-code-72':
        print(e)
"
```

This is how you see, for example, the heavy-hex-vs-all-to-all transpile-cost blowup for the QEC circuits without re-running anything — it's a durable artifact, and CI uploads it (`pipeline-metrics`) on every run.

## CI

`.github/workflows/ci.yml` defines two jobs:

- **`pr-pipeline`** (runs on every push/PR to `main`): lint, framework/contract tests, stages 2–5 (seed + generic), uploads `metrics.json`. This gates merges.
- **`nightly-hardware`** (cron, or manual `workflow_dispatch`): Stage 6 smoke test. `continue-on-error: true` — it never blocks a merge, because real hardware calls are inherently flaky.

Adding a circuit requires **no CI edit** — the generic test files it exercises are already wired into `pr-pipeline`.

## Debugging a failing invariant

Invariant failures include the circuit name, parameters, invariant name, and its `message`:

```
AssertionError: bb-code-72: invariant 'hamming_weight_exact[3]' failed —
All non-negligible-amplitude basis states must have Hamming weight 3
```

To reproduce outside pytest:

```python
from qloop.core.registry import registry
from qiskit.quantum_info import Statevector

spec = registry.get("dicke")
qc = spec.build(k=3)
sv = Statevector(qc)
for inv in spec.invariants_for(k=3):
    print(inv.name, inv.check(qc, sv))
```
