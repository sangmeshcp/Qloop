# Testing

## Test tiers

| Directory | What | Circuit-agnostic? |
|-----------|------|---------------------|
| `tests/test_framework/` | Registry discovery, deduplication, `by_tag()`; contract compliance for every registered spec | Yes — parametrized over `registry.all()` |
| `tests/generic/` | The six-stage pipeline itself, parametrized over `registry.all() × targets` | Yes |
| `tests/test_exact/`, `test_properties/`, `test_transpile/`, `test_noisy/` | Original hand-written tests predating the plugin framework, covering `bell`/`grover`/`vqe` specifically | No — kept for continuity |

**New circuits only need `tests/generic/` and `tests/test_framework/` to pass — you never write a new test file.** The hand-written tests in the other four directories exist because they predate the registry and were kept rather than deleted; nothing requires new circuits to have an equivalent.

## Contract tests

`tests/test_framework/test_contract.py` parametrizes `TestCircuitContract` over every registered spec and checks structural properties: `name` is a non-empty string, `n_qubits` is a positive int matching `build()`'s actual output, `budget()` returns a `Budget` with positive values, `param_space()`/`stim_param_space()` return `ParamSpace` instances, `reference_state()`/`expected_distribution()` return the right type or `None`, and — specifically — that any circuit with `n_qubits > MAX_STATEVECTOR_QUBITS` declares neither `reference_state()` nor `expected_distribution()` (since nothing downstream should ever try to build a `Statevector` for it).

If you add a circuit and its class attributes are malformed in some structural way, this is almost always where it'll be caught, with a clear per-check failure message rather than a downstream crash three layers deep in a generic test.

## Generic (registry-driven) tests

Each file in `tests/generic/` follows the same shape:

```python
_ALL = registry.all()

@pytest.mark.parametrize("spec", _ALL, ids=[s.name for s in _ALL])
def test_something(spec):
    value = spec.some_optional_method()
    if value is None:
        pytest.skip(f"{spec.name}: no some_optional_method defined")
    # ... assert something about value
```

The `pytest.skip()` with a circuit-specific reason is what makes an omitted optional declaration *visible* in test output rather than silently absent. When you're checking whether a new circuit is wired up correctly, run with `-v` and look for its name in the skip list — if a stage you expected to run shows as skipped, check that the corresponding `CircuitSpec` method is actually implemented (a common mistake: implementing `invariants()` but expecting the noisy tier to also run — it won't, that needs `expected_distribution()` separately).

## The Stim/Clifford tier

`tests/generic/test_stim_all.py` is structurally the same pattern, but drives `stim_program()`/`stim_param_space()` instead of the statevector-based methods, and its assertion is specific to detector semantics:

```python
sampler = prog.compile_detector_sampler()
detectors = sampler.sample(shots=4)
if error_injected:
    assert detectors.any()       # a detector must fire
else:
    assert not detectors.any()   # must be quiescent
```

Both `bb-code-72` and `bb-code-144` sweep `error_qubit` (including `-1` for "no error") via `stim_param_space()`, so this single test file exercises both the no-error quiescence case and single-qubit-error sensitivity, at both code sizes, without any code specific to either circuit.

## Debugging one circuit

```bash
pytest tests/generic/ tests/test_framework/ -v -k "my-circuit"
```

If a test is skipped when you expected it to run, check which `CircuitSpec` method that stage depends on (see the table in [Architecture](architecture.html#the-six-pipeline-stages)) and confirm you actually implemented it — not just wrote a docstring saying you would.

If an invariant fails, see [Usage → Debugging a failing invariant](usage.html#debugging-a-failing-invariant) for how to reproduce it outside pytest.

## A real bug this test suite caught

Worth internalizing before you assume your own circuit's construction is correct just because it looks right: the bivariate-bicycle QEC syndrome-extraction circuit (`bb_code_72.py`) went through an initial CNOT scheduling scheme that was provably conflict-free — no qubit was reused within a single tick, verified by direct enumeration. It still produced a circuit whose two-round syndrome detectors were **not** quiescent in the noiseless case — a bug that a purely structural/static check (like the conflict-freedom argument) could not catch, because conflict-freedom is necessary but not sufficient for correct stabilizer-measurement circuit ordering. It was caught only by actually simulating the circuit with Stim and observing non-deterministic detector outcomes. If you're implementing something with any circuit-ordering subtlety (multiple ancillas, multiple check types sharing qubits, teleportation-style postselection), **simulate before you trust a structural argument.**
