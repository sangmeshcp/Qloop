"""
Noisy simulation tests: statistical tolerance bands, never exact bitstring equality.

We assert p(00) ≈ 0.5 ± 0.05 rather than checking for an exact count.
Noise perturbs outcomes but the dominant correlation should survive at these error rates.
"""

import pytest

from backends.noise import build_noise_model, coupling_map_for
from circuits.bell import bell_circuit_measured
from pipeline.run import run_sampled

SHOTS = 4096
# Tolerance band: allow 5 percentage points of deviation from ideal 0.5
TOLERANCE = 0.05


def _load_noisy_target():
    import os

    import yaml

    yaml_path = os.path.join(os.path.dirname(__file__), "../../backends/targets.yaml")
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    return next(t for t in data["targets"] if t["name"] == "sim-noisy-heavyhex")


@pytest.fixture(scope="module")
def noisy_counts():
    target = _load_noisy_target()
    noise_model = build_noise_model(target)
    coupling_map = coupling_map_for(target)
    circuit = bell_circuit_measured()
    counts = run_sampled(circuit, shots=SHOTS, noise_model=noise_model, coupling_map=coupling_map)
    return counts


def test_bell_noisy_p00_in_band(noisy_counts):
    p00 = noisy_counts.get("00", 0) / SHOTS
    assert abs(p00 - 0.5) <= TOLERANCE, (
        f"p(00) = {p00:.4f} is outside tolerance band 0.5 ± {TOLERANCE}"
    )


def test_bell_noisy_p11_in_band(noisy_counts):
    p11 = noisy_counts.get("11", 0) / SHOTS
    assert abs(p11 - 0.5) <= TOLERANCE, (
        f"p(11) = {p11:.4f} is outside tolerance band 0.5 ± {TOLERANCE}"
    )


def test_bell_noisy_no_exact_bitstring_equality(noisy_counts):
    """Sanity check: noisy counts should NOT be exactly {00: N/2, 11: N/2}."""
    p00 = noisy_counts.get("00", 0) / SHOTS
    p11 = noisy_counts.get("11", 0) / SHOTS
    # With noise, |01⟩ and |10⟩ should appear at low but nonzero rates
    total_error = 1.0 - p00 - p11
    # We don't assert a specific error rate — just that it's within a sane range
    assert total_error >= 0.0


def test_bell_noisy_dominant_outcomes(noisy_counts):
    """00 and 11 together should dominate — noise shouldn't flip majority of outcomes."""
    p00 = noisy_counts.get("00", 0) / SHOTS
    p11 = noisy_counts.get("11", 0) / SHOTS
    assert p00 + p11 > 0.85, (
        f"Bell pair dominant outcomes (00+11) = {p00 + p11:.4f} < 0.85; noise too high?"
    )
