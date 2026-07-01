# Extending the framework

This page is about changes that go deeper than adding one circuit — new invariants, new backend targets, new domain types, or new contract methods. If you just want to add a circuit, see [Adding a circuit](adding-a-circuit.html) instead; you should almost never need anything on this page for that.

## Adding a reusable invariant

`qloop/core/invariants.py` is a flat list of factory functions, each returning an `Invariant(name, check, message)`. Add a new one when a check is useful across more than one circuit (if it's genuinely circuit-specific, define it inline in that circuit's `invariants_for()` instead — see `gqsp.py`'s `block_encoding_amplitude` check for an example of a one-off inline invariant).

```python
def my_invariant(threshold: float) -> Invariant:
    def check(circuit: QuantumCircuit, sv: Statevector) -> bool:
        # circuit and sv are the built QuantumCircuit and its exact Statevector
        return some_property(sv) > threshold

    return Invariant(
        name=f"my_invariant[{threshold}]",
        check=check,
        message=f"Some property must exceed {threshold}",
    )
```

`check` always receives `(circuit, statevector)` — never a shot-sampled distribution. Invariants are for properties checkable exactly against the ideal statevector; statistical properties belong in `expected_distribution()`, checked by the noisy tier's tolerance-band mechanism.

## Adding a new `ParamSpace` domain type

`qloop/core/spec.py` defines `_Domain` and its subclasses (`BitstringDomain`, `FloatDomain`, `IntDomain`, `ChoiceDomain`). Adding a new one means also adding a branch to `strategies_for()` in `qloop/core/strategies.py` mapping it to a `hypothesis.strategies` generator. `ChoiceDomain` (added for `bb_code_72.py`'s Pauli-basis error-injection sweep, `("X", "Z")`) is a reasonable template for a discrete non-numeric domain.

## Adding a new backend target

Edit `qloop/backends/targets.yaml`. Each target needs `name`, `type` (`"statevector"` or `"noisy"`), and for noisy targets: `coupling` (`"heavy-hex"` or anything else — anything else is treated as all-to-all), `basis_gates`, `depolarizing_1q`, `depolarizing_2q`. The `budget` key under each noisy target is **legacy** — it's only consulted by the four original hand-written seed-circuit tests (`tests/test_transpile/test_matrix.py`); every `CircuitSpec`-based circuit declares its own per-target budget via `Budget.for_target()` instead, so a new target doesn't need a `budget` key to work with the generic tests.

If your new target's basis gates can't reach some circuits' native gates (Qiskit's `BasisTranslator` needs an explicit equivalence rule for some gate pairs — see the `H → RY+RZ` registration in `qloop/pipeline/transpile.py` for why this was needed for the existing all-to-all target), you may need to add a similar `SessionEquivalenceLibrary.add_equivalence()` call.

## Adding a new optional `CircuitSpec` contract method

This is the biggest kind of change and should be rare — it means a genuinely new *kind* of verification the existing six methods can't express. The Stim tier (`stim_program()` + `stim_param_space()`, added when the framework's first 144-qubit circuit needed verification that couldn't route through `Statevector`) is the precedent to follow:

1. Add the method to `CircuitSpec` in `qloop/core/spec.py` with a default that causes a visible skip (`return None`, not an exception) — the framework's central invariant (missing declaration → visible skip, never silent pass) must hold for the new method too.
2. Add a new generic test file in `tests/generic/` that iterates `registry.all()`, skips circuits where the new method returns the "not declared" sentinel, and asserts whatever the new verification actually checks.
3. Add a contract test in `tests/test_framework/test_contract.py` checking the new method's return type.
4. Wire the new generic test file into `.github/workflows/ci.yml`'s `pr-pipeline` job.
5. Document it in [Adding a circuit](adding-a-circuit.html) alongside the existing optional methods.

Steps 2–4 are a one-time cost — after that, every circuit (existing and future) that can make use of the new method benefits with zero further edits, which is the entire point of doing this instead of writing a one-off test for a single circuit.

One thing this framework deliberately has **not** built, despite a plausible need: postselected/conditional statistics for the noisy tier (`magic_cultivation.py` needed this and worked around it with analytical invariants instead — see its docstring). If you need this, it's a legitimate candidate for the pattern above.
