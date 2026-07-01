# Adding a Circuit to Qloop

One new file is all it takes. Drop `qloop/circuits/my_circuit.py` in, run pytest, and every pipeline stage runs automatically.

---

## Step 1 — Copy the template

```bash
cp templates/circuit_template.py qloop/circuits/my_circuit.py
```

## Step 2 — Fill in the required fields

Open `qloop/circuits/my_circuit.py` and edit:

| Field | What to set |
|-------|-------------|
| `name` | Unique string identifier (lowercase, hyphens ok) |
| `n_qubits` | Number of qubits `build()` returns |
| `build(**params)` | Return a `QuantumCircuit` with no measurements |
| `budget()` | Max depth / two-qubit gate count after transpilation |

That's it for the minimum viable plugin.

## Step 3 — Run the suite

```bash
pytest tests/test_framework/ tests/generic/ -v
```

You'll see your circuit appear in every parametrized test automatically.

---

## Optional declarations and what they unlock

Each optional method you add enables one more pipeline stage. Omitting it produces a visible `pytest.skip` — never a silent pass.

### `reference_state(**params) → Statevector`
Enables **Stage 2** exact statevector comparison. Define this when the output state has a known closed form (Bell, GHZ, etc.).

```python
def reference_state(self, **params) -> Statevector:
    inv_sqrt2 = 1.0 / np.sqrt(2)
    return Statevector([inv_sqrt2, 0.0, 0.0, inv_sqrt2])
```

### `reference_expectation(**params) → float`
Enables exact expectation-value checking in Stage 2 — useful for variational circuits (VQE ground state energy).

### `invariants() → list[Invariant]`
Enables **Stage 3** property checks at default parameters. `normalized()` is always checked automatically.

```python
from qloop.core.invariants import normalized, unitary

def invariants(self):
    return [normalized(), unitary()]
```

### `invariants_for(**params) → list[Invariant]`
Override instead of `invariants()` when the correct invariants depend on parameters (e.g. Grover's marked state changes).

### `param_space() → ParamSpace`
Enables **Stage 3** Hypothesis fuzzing — the framework generates random parameter combinations and checks `invariants_for` across all of them.

```python
from qloop.core.spec import BitstringDomain, FloatDomain, ParamSpace

def param_space(self) -> ParamSpace:
    return ParamSpace(
        marked=BitstringDomain(length=2),
        theta=FloatDomain(0.0, 3.14159),
    )
```

### `expected_distribution(**params) → dict[str, float]`
Enables **Stage 5** noisy simulation. Keys are bitstrings; values are ideal probabilities. The noisy test asserts each observed probability falls within ±7 pp of the ideal.

```python
def expected_distribution(self, **params) -> dict[str, float]:
    return {"00": 0.5, "11": 0.5}
```

### `stim_program(**params) → stim.Circuit | None`, `stim_param_space() → ParamSpace`
Enables **Stage 3b**, the Clifford/Stim tier — for Clifford circuits too large for statevector simulation (`n_qubits > MAX_STATEVECTOR_QUBITS`, currently 20). Return a `stim.Circuit` with `DETECTOR` instructions; the generic test asserts detectors are quiescent absent an injected error and fire when one is injected (by convention, sweep an `error_qubit` parameter where `-1` means "no error"). `stim_param_space()` is independent from `param_space()` — they drive different sweeps (Stim error injection vs. statevector-based Hypothesis fuzzing).

```python
def stim_program(self, error_qubit: int = -1, **params):
    circuit = stim.Circuit()
    # ... build a 2-round syndrome-extraction circuit with DETECTOR instructions
    return circuit

def stim_param_space(self) -> ParamSpace:
    return ParamSpace(error_qubit=IntDomain(-1, self.n_qubits - 1))
```

If your circuit is small enough for statevector simulation, you don't need this — `reference_state()` and `invariants()` are simpler and sufficient. This tier exists specifically for the handful of circuits (`bb-code-72`, `bb-code-144`) at 144+ qubits.

---

## Budget tuning

`Budget` has two pairs of limits:

```python
Budget(
    depth=50,                  # ideal or all-to-all targets
    two_qubit_gates=15,
    depth_limited=80,          # heavy-hex: SWAP overhead inflates depth
    two_qubit_gates_limited=25,
)
```

If you omit `depth_limited`, the `depth` value is used for all targets. Tighten the budget after measuring actual transpiled depth (Stage 4 prints `[metrics]` lines under `pytest -s`).

---

## Example: GHZ (minimal plugin)

`qloop/circuits/ghz.py` is the canonical example:

- Has `reference_state` → Stage 2 runs.
- Has `invariants_for` (plus `param_space` sweeping `n`) → Stage 3 runs, fuzzed.
- Has `budget` → Stage 4 runs.
- **No `expected_distribution`** → Stage 5 produces a visible skip.

To re-enable Stage 5 for GHZ at its default n=12, add:

```python
def expected_distribution(self, n: int = DEFAULT_N, **params) -> dict[str, float]:
    return {"0" * n: 0.5, "1" * n: 0.5}
```

See also `qloop/circuits/ghz_tree.py` — same target state, a different (log-depth) construction, registered as a *separate* circuit specifically so both get independent budgets checked by the transpile matrix. That's the pattern to follow whenever you want to compare two constructions of the same thing: two `CircuitSpec`s, not one circuit with a "which construction" parameter (budgets aren't parametrized, so a single circuit can't get two different budget checks).

---

## What the framework never requires

- No edits to `tests/` — all generic tests iterate `registry.all()`.
- No edits to `conftest.py` or CI config.
- No import lists or registration calls — discovery is automatic.
