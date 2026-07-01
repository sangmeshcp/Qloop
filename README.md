# Qloop

A quantum-circuit SDLC framework on classical simulators. Six pipeline stages, a plugin registry for auto-discovered circuits, exact + noisy + property test tiers, transpilation-as-build-target, and a green CI pipeline. Hardware tier is stubbed and gated.

**Stack:** Qiskit 2.4 + Qiskit Aer 0.17 · Stim · Python 3.11 · pytest + hypothesis · GitHub Actions

All library code lives under `qloop/` — circuits, backends, pipeline helpers, and the plugin framework itself are a single package. Any circuit dropped as a single file in `qloop/circuits/` is automatically discovered and covered by all six pipeline stages. See [docs/ADDING_A_CIRCUIT.md](docs/ADDING_A_CIRCUIT.md).

---

## The Six Pipeline Stages

| Stage | What | Where |
|-------|------|--------|
| 1 | **Lint & static** — ruff, circuit builds, qubit-budget check. Fast fail. | `ruff check .` |
| 2 | **Exact verification** — statevector vs known-good, deterministic. | `tests/test_exact/` + `tests/generic/test_exact_all.py` |
| 3 | **Property tests** — invariants via Hypothesis, sweeps all inputs; large Clifford circuits route through Stim instead of statevector. | `tests/test_properties/` + `tests/generic/test_properties_all.py` + `tests/generic/test_stim_all.py` |
| 4 | **Transpilation matrix** — compile per target, assert fits budget. | `tests/test_transpile/` + `tests/generic/test_transpile_all.py` |
| 5 | **Noisy simulation** — noise models, statistical tolerance bands. | `tests/test_noisy/` + `tests/generic/test_noisy_all.py` |
| 6 | **Hardware smoke** — async, gated, stubbed. Never blocks merges. | CI `nightly-hardware` job |

Stages 1–5 gate every PR. Stage 6 runs nightly (or on-demand via `workflow_dispatch`) and is marked `continue-on-error: true`.

---

## Circuit Corpus

17 circuits registered under `qloop/circuits/`, added in tiers that progressively stress different pipeline stages. Every circuit is auto-discovered — the tier structure below is a narrative for humans, not something the pipeline knows about.

| Tier | Circuits | What it stresses |
|------|----------|-------------------|
| 0 — seed benchmarks | `ghz`, `ghz-tree`, `qft`, `tfim-trotter`, `mermin-bell` | Airtight closed-form oracles; validates all six stages end to end |
| 1 — Clifford QEC | `bb-code-72` | 144-qubit circuit, verified via Stim instead of statevector; heavy-hex vs all-to-all transpile blowup |
| 2 — non-Clifford exact oracles | `color-832-ccz`, `dicke`, `gqsp` | Exact statevector/amplitude targets derived and verified from scratch (not memorized formulas) |
| 3 — topology + statistics | `qaoa-maxcut`, `qaoa-ring`, `quantum-volume` | Same ansatz, different graph locality; the canonical noisy-tier statistical benchmark |
| 4 — hard tier | `bb-code-144`, `magic-cultivation` | 288-qubit Stim-only circuit; postselected/conditional statistics |
| (base) | `bell`, `grover`, `vqe` | The original pre-framework circuit set |

Two circuits are worth calling out because their *measured* result isn't the naively expected one:

- **`ghz` vs `ghz-tree`** (same GHZ state, ladder vs log-depth-tree construction, same qubit count): the tree has less than half the ladder's logical depth, but costs *more* two-qubit gates once transpiled onto heavy-hex, because its long-range CNOTs need SWAP routing that the ladder's already-local CNOTs don't. Logical depth and post-transpile hardware cost are not the same thing — which is the entire reason Stage 4 exists.
- **`bb-code-72`/`bb-code-144`**: an initial 6-tick CNOT schedule that was conflict-free by simple qubit-reuse counting turned out, when actually simulated, to produce non-deterministic syndromes. Conflict-freedom is necessary but not sufficient for circuit correctness — caught only by running the circuit, not by inspecting the schedule.

Every paper-derived circuit's docstring states plainly which claims were independently verified (via a from-scratch cross-check — different code, same math, checked to agree) versus which parts of the source paper were deliberately not reproduced because they couldn't be verified with confidence. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design rationale and [docs/ADDING_A_CIRCUIT.md](docs/ADDING_A_CIRCUIT.md) to add your own.

---

## Two Assertion Styles

**Exact (deterministic):** Statevector comparisons with `np.testing.assert_allclose`. The Bell state must be exactly `[1/√2, 0, 0, 1/√2]`; Grover's marked state must have dominant amplitude. These tests never use shots.

**Statistical (tolerance bands):** Noisy tests sample thousands of shots and assert probabilities fall within ±5 percentage points of the ideal value. We assert `|p(00) − 0.5| ≤ 0.05`, never `counts["00"] == 2048`. This is the only correct way to test probabilistic circuits — exact bitstring equality would produce flaky tests that fail at random.

---

## Transpilation as a Build Target (Stage 4)

Stage 4 is the quantum equivalent of a compile step. Each circuit is transpiled to every backend target's native gate set and topology, then checked against a depth and two-qubit-gate budget:

```yaml
# qloop/backends/targets.yaml — budget knob
budget:
  depth: 60          # max circuit depth after transpilation
  two_qubit_gates: 20  # max 2Q gate count (expensive, noisy)
```

If a circuit exceeds the budget, `BudgetExceeded` is raised and the test fails — exactly as a build fails when a binary is too large or a latency SLO is violated. Tighten the budget to catch circuits that over-decompose.

---

## Topology Comparison: Heavy-Hex vs All-to-All

| Property | Heavy-hex (superconducting) | All-to-all (trapped ion) |
|----------|-----------------------------|--------------------------|
| Connectivity | Sparse, scales with circuit size (`CouplingMap.from_heavy_hex`) | Fully connected, scales with circuit size (`CouplingMap.from_full`) |
| Basis gates | `rz, sx, x, cx` | `cx, ry, rz` (see targets.yaml for why not native `rxx`) |
| SWAP overhead | High — routing adds SWAPs | None — no routing needed |
| 2Q error rate | ~1% | ~0.5% |
| Legacy seed-circuit budget | depth 120, 2q 30 | depth 40, 2q 15 |

Each `CircuitSpec` declares its own `Budget()` (see the Circuit Corpus section above) with separate limits for heavy-hex (`depth_limited`/`two_qubit_gates_limited`) vs. all other targets — the numbers above are only the legacy fixed budget still used by the original `tests/test_transpile/test_matrix.py` seed-circuit tests. The `sim-noisy-heavyhex` target approximates IBM-style superconducting qubits; `sim-noisy-alltoall` approximates trapped-ion processors like IonQ or Quantinuum.

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run all stages 2–5
pytest

# Run individual stages
pytest tests/test_exact/ tests/generic/test_exact_all.py             # Stage 2
pytest tests/test_properties/ tests/generic/test_properties_all.py   # Stage 3
pytest tests/generic/test_stim_all.py                                # Stage 3b (Clifford/Stim)
pytest tests/test_transpile/ tests/generic/test_transpile_all.py -s  # Stage 4 (prints metrics)
pytest tests/test_noisy/ tests/generic/test_noisy_all.py             # Stage 5

# Lint
ruff check .
```

---

## Hardware Extension Point (Stage 6)

`qloop/pipeline/run.py::submit_hardware` is the extension point for real hardware. It currently raises `NotImplementedError` with the async shape documented in its docstring:

```
1. SUBMIT  — POST circuit to provider API → receive job_id
2. POLL    — GET job status on exponential backoff until COMPLETED/FAILED
3. RETRIEVE — fetch counts, decode to dict[str, int], return
```

Wire in `qiskit-ibm-runtime`, `amazon-braket-sdk`, or `qiskit-ionq` here. The nightly CI job already calls this stub for all three targets — it just verifies the `NotImplementedError` fires correctly until a real backend is wired.

---

## The Honest Gap: Sim ≠ Hardware Past ~30–40 Qubits

Classical statevector simulation requires 2ⁿ complex amplitudes — 40 qubits needs 16 TB of RAM, 50 qubits is intractable on any classical machine. This repo validates circuit *logic* classically, but:

- **Crosstalk** between nearby qubits is not modeled (only depolarizing noise is).
- **Coherence times** (T1/T2) and pulse-level distortions are absent.
- **Measurement error** and readout asymmetry are not included.
- **Calibration drift** means a circuit that worked yesterday may not today.

Treat sim-green as a necessary but not sufficient condition for hardware success. The gap closes as error-mitigation (ZNE, PEC) and error-correction (surface codes) mature.

---

## Repo Layout

```
qloop/
  core/           CircuitSpec contract, registry, invariants, param strategies
  circuits/       17 plugin modules (drop new ones here — see the Circuit
                  Corpus table above and docs/ADDING_A_CIRCUIT.md).
                  _qaoa_common.py and _bb_code_common.py are shared helpers,
                  not circuits — the registry skips modules with no
                  concrete CircuitSpec subclass.
  backends/       targets.yaml (topology/noise config) + noise model builder
  pipeline/       transpile + run helpers + hardware stub + metrics collector

templates/        circuit_template.py — copy-me starter for new plugins
docs/             ARCHITECTURE.md, ADDING_A_CIRCUIT.md — see docs/README.md

tests/
  test_framework/   Registry unit tests + contract tests (all specs)
  generic/          Stage 2–5 parametrized over registry.all() × targets,
                    plus the Stim/Clifford path for large circuits
  test_exact/       Stage 2: original Bell + Grover deterministic checks
  test_properties/  Stage 3: original Hypothesis invariants
  test_transpile/   Stage 4: original transpilation build matrix
  test_noisy/       Stage 5: original Bell noisy tolerance-band checks

.github/workflows/  CI: pr-pipeline (stages 1–5) + nightly-hardware (stage 6)
```
