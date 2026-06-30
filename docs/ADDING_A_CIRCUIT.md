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
- Has `invariants` → Stage 3 runs.
- Has `budget` → Stage 4 runs.
- **No `expected_distribution`** → Stage 5 produces a visible skip.

To re-enable Stage 5 for GHZ, add:

```python
def expected_distribution(self, **params) -> dict[str, float]:
    return {"000": 0.5, "111": 0.5}
```

---

## What the framework never requires

- No edits to `tests/` — all generic tests iterate `registry.all()`.
- No edits to `conftest.py` or CI config.
- No import lists or registration calls — discovery is automatic.
