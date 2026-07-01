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
| Connectivity | Sparse, linear-ish coupling | Any qubit can directly interact |
| Native 2Q gate | `cx` | `rxx` |
| SWAP overhead | High — routing adds SWAPs | None — no routing needed |
| 2Q error rate | ~1% | ~0.5% |
| Depth budget | 60 (more slack for SWAPs) | 40 (tight; no SWAP waste) |
| Speed | GHz clock, fast per gate | Slower per gate, fewer gates needed |

The `sim-noisy-heavyhex` target approximates IBM-style superconducting qubits. The `sim-noisy-alltoall` target approximates trapped-ion processors like IonQ or Quantinuum.

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
  circuits/       Plugin modules: bell, grover, vqe, ghz, qft, tfim_trotter,
                  mermin_bell, bb_code_72 (drop new ones here)
  backends/       targets.yaml (topology/noise config) + noise model builder
  pipeline/       transpile + run helpers + hardware stub + metrics collector

templates/        circuit_template.py — copy-me starter for new plugins
docs/             ADDING_A_CIRCUIT.md — authoring guide

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
