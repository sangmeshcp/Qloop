"""
Pipeline metrics collector.

Records (circuit, target, stage) metrics during a test session and writes
a structured JSON file on completion.  Import the module-level singleton:

    from qloop.pipeline.report import metrics

    metrics.record("bell", "sim-ideal", "transpile", depth=3, two_qubit_gates=1)

Then call metrics.flush_to_file("metrics.json") in a pytest sessionfinish hook.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path


class MetricsCollector:
    """Thread-safe singleton that accumulates pipeline metrics across a session."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: list[dict] = []

    def record(self, circuit: str, target: str, stage: str, **kwargs) -> None:
        """Append one measurement row."""
        entry = {"circuit": circuit, "target": target, "stage": stage, **kwargs}
        with self._lock:
            self._entries.append(entry)

    def all(self) -> list[dict]:
        """Return a snapshot of all recorded entries."""
        with self._lock:
            return list(self._entries)

    def flush_to_file(self, path: str | Path) -> None:
        """Write all collected entries to a JSON file.  Creates parent dirs if needed."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            data = list(self._entries)
        with open(p, "w") as f:
            json.dump({"entries": data}, f, indent=2)

    def reset(self) -> None:
        """Clear all entries (useful between test runs)."""
        with self._lock:
            self._entries.clear()


metrics = MetricsCollector()
