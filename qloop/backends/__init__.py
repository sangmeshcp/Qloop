"""Backend utilities: target loading and noise configuration."""

from __future__ import annotations

from pathlib import Path

import yaml

_YAML_PATH = Path(__file__).resolve().parent / "targets.yaml"


def load_targets() -> list[dict]:
    """Load and return the list of target dicts from targets.yaml."""
    with open(_YAML_PATH) as f:
        data = yaml.safe_load(f)
    return data["targets"]


def noisy_targets() -> list[dict]:
    """Return only targets of type 'noisy' (i.e. that have a noise model)."""
    return [t for t in load_targets() if t.get("type") == "noisy"]
