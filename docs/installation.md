# Installation

## Requirements

- Python 3.11
- pip

Qloop pins exact versions in `requirements.txt` — Qiskit 2.4.2, Qiskit Aer 0.17.2, Stim 1.16.0, pytest 9.1.1, hypothesis 6.155.7, plus supporting libraries. Version drift in Qiskit especially is worth avoiding: several parts of this codebase (the `SessionEquivalenceLibrary` registration in `qloop/pipeline/transpile.py`, `CouplingMap.from_heavy_hex`) depend on Qiskit 2.x-specific behavior.

## Setup

```bash
git clone https://github.com/sangmeshcp/Qloop.git
cd Qloop
pip install -r requirements.txt
```

No virtual environment is enforced by the repo, but using one is recommended:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Verify the install

```bash
pytest tests/test_framework/ -v
```

This runs the registry and contract tests only (fast, no simulation) — if this passes, the plugin framework itself is sound. Then run the full suite:

```bash
pytest
```

Expect this to complete in well under a minute and report something like `4XX passed, 6X skipped` — the skips are expected (see [Architecture](architecture.html#the-six-pipeline-stages) for why circuits skip stages) and should never be zero across the whole run (that would mean the skip mechanism itself broke).

```bash
ruff check .
```

Should report `All checks passed!`. CI runs this as Stage 1 and treats any lint failure as a hard fail.

## Troubleshooting

**`ModuleNotFoundError: No module named 'stim'`** — Stim is required for the Clifford/QEC circuits (`bb-code-72`, `bb-code-144`). It's in `requirements.txt`; if you installed dependencies manually rather than via `pip install -r requirements.txt`, add it: `pip install stim==1.16.0`.

**Transpiler errors mentioning `BasisTranslator` or "Unable to translate"** — this usually means `qloop/pipeline/transpile.py` wasn't imported before a raw `qiskit.transpile()` call elsewhere (its module-level `_register_ry_rz_equivalences()` call is what makes the all-to-all target's `{cx, ry, rz}` basis reachable from `H`/`X` gates). Import `qloop.pipeline.transpile` (or anything that imports it, like `qloop.backends.noise`) before transpiling.

**Tests hang or take unusually long** — the two 288-qubit circuits (`bb-code-144`) route entirely through Stim, not statevector simulation, and should complete in well under a second even for the Stim tier. If something in the exact/property tier is hanging, check that `spec.n_qubits > MAX_STATEVECTOR_QUBITS` guards are actually being hit (they should skip, not attempt a `2^288`-dimensional `Statevector`).
