"""Root conftest: session-level hooks shared across all test tiers."""

from __future__ import annotations

from qloop.pipeline.report import metrics


def pytest_sessionfinish(session, exitstatus) -> None:
    """Write accumulated pipeline metrics to metrics.json after all tests finish."""
    metrics.flush_to_file("metrics.json")
