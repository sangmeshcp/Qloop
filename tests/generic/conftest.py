"""Fixtures shared across generic test modules."""

from __future__ import annotations

import pytest

from qloop.backends import load_targets, noisy_targets
from qloop.core.registry import registry
from qloop.core.spec import CircuitSpec


@pytest.fixture(scope="session")
def all_specs() -> list[CircuitSpec]:
    return registry.all()


@pytest.fixture(scope="session")
def all_targets() -> list[dict]:
    return load_targets()


@pytest.fixture(scope="session")
def noisy_target_list() -> list[dict]:
    return noisy_targets()
