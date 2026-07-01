# Architecture

## The core idea

Qloop separates **circuit content** (what a circuit does, and what "correct" means for it) from **pipeline mechanics** (how correctness gets checked). A circuit author writes one file implementing a small contract; the framework's generic tests iterate over every registered circuit and run whichever checks that circuit's contract implementation makes possible. Nothing in the test suite, CI config, or a registration list needs to change when a circuit is added.

This is possible because of three things working together: the `CircuitSpec` contract, the auto-discovery registry, and generic (registry-driven) test files instead of one test file per circuit.

## `CircuitSpec` — the plugin contract

Defined in `qloop/core/spec.py`. Every circuit plugin subclasses this.

```python
class CircuitSpec(ABC):
    name: ClassVar[str]
    n_qubits: ClassVar[int]
    tags: ClassVar[list[str]] = []

    @abstractmethod
    def build(self, **params) -> QuantumCircuit: ...

    def reference_state(self, **params) -> Statevector | None: ...      # Stage 2
    def reference_expectation(self, **params) -> float | None: ...      # Stage 2
    def invariants(self) -> list[Invariant]: ...                        # Stage 3
    def invariants_for(self, **params) -> list[Invariant]: ...          # Stage 3
    def param_space(self) -> ParamSpace: ...                            # Stage 3 (fuzzing)
    def budget(self) -> Budget: ...                                     # Stage 4
    def expected_distribution(self, **params) -> dict[str, float] | None: ...  # Stage 5
    def stim_program(self, **params): ...                               # Stage 3b (Clifford/Stim)
    def stim_param_space(self) -> ParamSpace: ...                       # Stage 3b
```

Only `build()`, `name`, and `n_qubits` are required. Every other method has a default (`None`, `[]`, or `ParamSpace.empty()`) that causes the corresponding pipeline stage to **skip visibly** for that circuit — never a silent pass. This is the framework's central design invariant: a missing declaration is always observable in test output, never invisible.

### Supporting types

- **`Invariant(name, check, message)`** — `check` is `(circuit, statevector) -> bool`. Factory functions live in `qloop/core/invariants.py`: `normalized()`, `unitary()`, `marked_dominant()`, `above_uniform()`, `hamming_weight_exact()`, `real_nonnegative_amplitudes()`, `heavy_output_probability_exceeds()`, `zz_expectation_equals()`, `hermitian_expectation()`. Add new ones here when a check is reusable across circuits.
- **`Budget(depth, two_qubit_gates, depth_limited, two_qubit_gates_limited)`** — `for_target(target)` picks the `_limited` variant when `target["coupling"] == "heavy-hex"`, else the base fields. The base fields apply to *every other* target (including `sim-ideal`), which matters when a circuit's ideal-target transpile leaves gates undecomposed (see the Stage 4 section below).
- **`ParamSpace(**domains)`** — declares a Hypothesis-fuzzable parameter space. Domain types: `BitstringDomain`, `FloatDomain`, `IntDomain`, `ChoiceDomain`. `qloop/core/strategies.py` maps each to a `hypothesis.strategies` generator.
- **`MAX_STATEVECTOR_QUBITS = 20`** — circuits above this qubit count must never be exercised through a `Statevector`. The generic exact/property tests check this and skip; circuits at this scale (the BB codes) verify through Stim instead (see below).

## The registry — auto-discovery

`qloop/core/registry.py`. A lazy singleton (`registry`, module-level). On first access (`registry.all()`, `registry.get()`, `registry.by_tag()`):

1. `pkgutil.iter_modules` walks `qloop/circuits/`, importing every module.
2. `CircuitSpec.__subclasses__()` (recursively) finds every subclass.
3. Filters: `__module__` must start with `qloop.circuits.` (so test-helper subclasses defined elsewhere never leak in), the class must be concrete (no unimplemented abstract methods), and it must have `name`/`n_qubits` set.
4. Each surviving subclass is instantiated and validated (`name` non-empty, `n_qubits` positive, `build()` returns a `QuantumCircuit`) and registered. A duplicate `name` raises immediately.

Two files in `qloop/circuits/` are *not* circuits — `_qaoa_common.py` and `_bb_code_common.py` hold logic shared between related circuit pairs (`qaoa-maxcut`/`qaoa-ring`, `bb-code-72`/`bb-code-144`). They define no `CircuitSpec` subclass, so discovery silently skips them. This is the supported pattern for sharing code between plugins without violating "one file per circuit."

## The six pipeline stages

| # | Stage | Driven by | Skip condition |
|---|-------|-----------|-----------------|
| 1 | Lint & static | `ruff check .` | n/a |
| 2 | Exact verification | `reference_state()` / `reference_expectation()` | Both `None`, or `n_qubits > MAX_STATEVECTOR_QUBITS` |
| 3 | Property tests | `invariants()` + `invariants_for()` + `param_space()` | `param_space()` empty → only default-params check runs |
| 3b | Clifford/Stim | `stim_program()` + `stim_param_space()` | `stim_program()` returns `None` |
| 4 | Transpilation matrix | `budget()` | Never skips — every registered circuit gets a budget |
| 5 | Noisy simulation | `expected_distribution()` | `None` |
| 6 | Hardware smoke | `qloop/pipeline/run.py::submit_hardware` | Stubbed; nightly only, `continue-on-error: true` |

Stages 1–5 (plus 3b) gate every PR via `tests/generic/*.py`, each parametrized over `registry.all() × targets` (or just `registry.all()` for stages 2/3/3b). Stage 6 runs nightly.

### Why stage 3b (Stim) exists

Two circuits in the corpus (`bb-code-72`, `bb-code-144`) are 144 and 288 qubits — far beyond `2^n`-amplitude statevector simulation, but Clifford-only, so a polynomial-time stabilizer simulator (Stim) can verify them exactly. `stim_program(**params)` returns a `stim.Circuit` with `DETECTOR` instructions; `tests/generic/test_stim_all.py` asserts detectors are quiescent absent an injected error and fire when one is injected. `stim_param_space()` is declared separately from `param_space()` because they drive genuinely different sweeps (Stim error-injection parameters vs. Hypothesis-fuzzed circuit parameters) — a circuit could in principle want both.

### Stage 4 in more depth: budgets are per-target, not per-circuit

`coupling_map_for(target, n_qubits)` in `qloop/backends/noise.py` generates a `CouplingMap` scaled to the circuit: `CouplingMap.from_heavy_hex(d)` for a `d` large enough to cover `n_qubits`, `CouplingMap.from_full(n_qubits)` for all-to-all. (For `n_qubits` at or below the size of the four original seed circuits, it falls back to small fixed maps for backward compatibility — this only matters if you're reading old code, not for new circuits.) Because `Budget.for_target()` only distinguishes heavy-hex from everything else, a circuit's `sim-ideal` and `sim-noisy-alltoall` budgets share the same (non-`_limited`) fields — this catches people off guard the first time (see `color_832_ccz.py`'s budget comment for a worked example where `sim-ideal` leaves a `StatePreparation` gate undecomposed, giving trivial depth, while `sim-noisy-alltoall` forces full decomposition to a much larger depth using that *same* budget field).

## `qloop/backends/` and `qloop/pipeline/`

- **`backends/__init__.py`**: `load_targets()` / `noisy_targets()` read `backends/targets.yaml` (three targets: `sim-ideal`, `sim-noisy-heavyhex`, `sim-noisy-alltoall`).
- **`backends/noise.py`**: `build_noise_model(target)` (depolarizing noise from the YAML's per-target error rates), `coupling_map_for(target, n_qubits=None)` (see above).
- **`pipeline/transpile.py`**: `transpile_for_target()` (wraps `qiskit.transpile`, returns `TranspileMetrics`), `assert_fits()` (raises `BudgetExceeded`). Registers `H → RY+RZ` and `X → RZ+RY` equivalences into Qiskit's `SessionEquivalenceLibrary` at import time — required because Qiskit 2.x's `BasisTranslator` doesn't include these by default, and the all-to-all target's basis is `{cx, ry, rz}`.
- **`pipeline/run.py`**: `run_ideal()` (statevector), `run_sampled()` (Aer shot-based sampling), `submit_hardware()` (stub, Stage 6's extension point).
- **`pipeline/report.py`**: `MetricsCollector`, a thread-safe singleton (`metrics`). Every generic transpile test calls `metrics.record(circuit, target, stage, **kwargs)`; the root `conftest.py`'s `pytest_sessionfinish` hook flushes it to `metrics.json` at the end of the run. This is how the heavy-hex-vs-all-to-all transpile-cost story (e.g. the BB codes' ~20x 2Q-gate blowup) gets captured as a durable artifact instead of only appearing in `-s` console output.

## Test suite structure

```
tests/
  test_framework/     Registry unit tests (discovery, dedup, by_tag) +
                       contract tests (every registered spec satisfies
                       CircuitSpec's structural requirements)
  generic/             The registry-driven tests: test_exact_all.py,
                       test_properties_all.py, test_stim_all.py,
                       test_transpile_all.py, test_noisy_all.py — each
                       iterates registry.all() (× targets where relevant)
  test_exact/          Original hand-written tests for bell/grover (predate
  test_properties/     the framework; kept for continuity, not required
  test_transpile/      for new circuits — the generic/ tests already cover
  test_noisy/          them)
```

**If you're adding a circuit, you never touch anything under `tests/`.** See [Adding a circuit](adding-a-circuit.html).

## What deliberately isn't built

A few things came up during development that were consciously *not* built, and it's worth knowing why rather than assuming they're oversights:

- **Circuit-level distance (`d_circ`) for the BB codes** — would need explicit logical-operator construction via Stim's `shortest_graphlike_error`, a substantial additional GF(2) computation. Both `bb_code_72.py` and `bb_code_144.py` state this as a known limitation.
- **Postselected/conditional statistics in the noisy tier** — `magic_cultivation.py` needs to check probabilities *conditioned on* an ancilla's measurement outcome, which `expected_distribution()`'s flat per-bitstring contract doesn't express. Verified instead via custom invariants operating analytically on the exact statevector.
- **Several circuits' source papers' specific novel algorithms** — where a paper's own construction couldn't be reliably reconstructed from a summary without risking a silent implementation bug (see `dicke.py`, `gqsp.py`, `magic_cultivation.py` docstrings), a simpler-but-verifiable substitute was built instead, with the scope reduction stated explicitly in the module docstring.

This pattern — state what wasn't done and why, rather than silently shipping an unverified reconstruction — comes directly from a real bug caught during development: an early bivariate-bicycle syndrome-extraction schedule *looked* correct by a simple qubit-conflict argument, but direct Stim simulation showed it produced non-deterministic syndromes. Conflict-freedom was necessary but not sufficient. The fix was verification, not more careful reasoning by inspection.
