"""Backend utilities: target loading and noise configuration."""

from __future__ import annotations

from pathlib import Path

import yaml

# Resolve once relative to this file so it works regardless of CWD.
_YAML_PATH = Path(__file__).resolve().parent.parent.parent / "backends" / "targets.yaml"


def load_targets() -> list[dict]:
    """Load and return the list of target dicts from backends/targets.yaml."""
    with open(_YAML_PATH) as f:
        data = yaml.safe_load(f)
    return data["targets"]


def noisy_targets() -> list[dict]:
    """Return only targets of type 'noisy' (i.e. that have a noise model)."""
    return [t for t in load_targets() if t.get("type") == "noisy"]
