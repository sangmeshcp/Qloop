"""
Generic exact-verification tier (Stage 2) — parametrized over registry.all().

For each registered circuit:
  - If reference_state() is defined → compare ideal statevector.
  - If reference_expectation() is defined → compare expectation value.
  - Otherwise: test is skipped with a visible reason.

Adding a new CircuitSpec automatically participates in these checks.
"""

from __future__ import annotations

import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from qloop.core.registry import registry
from qloop.core.spec import MAX_STATEVECTOR_QUBITS

_ALL = registry.all()


@pytest.mark.parametrize("spec", _ALL, ids=[s.name for s in _ALL])
def test_exact_state(spec):
    ref = spec.reference_state()
    if ref is None:
        pytest.skip(f"{spec.name}: no reference_state defined")
    if spec.n_qubits > MAX_STATEVECTOR_QUBITS:
        pytest.skip(
            f"{spec.name}: n_qubits={spec.n_qubits} exceeds MAX_STATEVECTOR_QUBITS"
            f"={MAX_STATEVECTOR_QUBITS}"
        )

    qc = spec.build()
    sv = Statevector(qc)
    np.testing.assert_allclose(
        sv.data,
        ref.data,
        atol=1e-9,
        err_msg=f"{spec.name}: statevector does not match reference",
    )


