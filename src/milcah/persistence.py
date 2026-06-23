"""Iterative refinement / persistence (FR10).

Persist a framework's analysis as a timestamped **snapshot** — the framework, its
reasoning units, the worldview ontology (placement + fractures), and the coherence
metrics — so a worldview's coherence can be tracked **over time** as it is
re-pressure-tested (FR10: scores, ontology state, fractures, assumptions,
unresolved nodes, trend over time).

Faithful to Milcah's design: the core is **dependency-free** and the backend is an
injectable seam (`Store`). The default `JsonFileStore` writes transparent JSON files
(no database, human-inspectable). A Tirzah-backed `Store` (the family memory layer,
per the architecture) is a later, optional backend that implements the same
protocol — nothing here imports it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from milcah.metrics import CoherenceMetrics, to_jsonable as metrics_to_jsonable
from milcah.models import Framework, ReasoningUnit
from milcah.models import to_jsonable as model_to_jsonable
from milcah.ontology import WorldviewOntology
from milcah.ontology import to_jsonable as ontology_to_jsonable

SCHEMA_VERSION = 1

# The coherence/debt metrics whose movement over time is the "trend" (FR10).
TREND_METRICS = (
    "global_coherence", "fracture_density", "uncertainty_burden",
    "ontological_completeness", "unresolved_load", "fallacy_load",
    "assumption_load", "node_count",
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash(*parts: str) -> str:
    import hashlib

    return hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()[:16]


@dataclass
class Snapshot:
    """One point-in-time analysis of a framework."""

    framework_id: str
    framework_title: str
    created_at: str
    metrics: dict[str, Any]
    framework: dict[str, Any] = field(default_factory=dict)
    units: list[dict[str, Any]] = field(default_factory=list)
    ontology: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    @property
    def snapshot_id(self) -> str:
        return _hash("snapshot", self.framework_id, self.created_at)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "framework_id": self.framework_id,
            "framework_title": self.framework_title,
            "created_at": self.created_at,
            "metrics": self.metrics,
            "framework": self.framework,
            "units": self.units,
            "ontology": self.ontology,
        }

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> "Snapshot":
        return cls(
            framework_id=data["framework_id"],
            framework_title=data.get("framework_title", ""),
            created_at=data["created_at"],
            metrics=data.get("metrics", {}),
            framework=data.get("framework", {}),
            units=data.get("units", []),
            ontology=data.get("ontology", {}),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )


def build_snapshot(
    framework: Framework,
    units: list[ReasoningUnit],
    ontology: WorldviewOntology,
    metrics: CoherenceMetrics,
    *,
    created_at: str | None = None,
) -> Snapshot:
    """Assemble a snapshot from the live analysis objects."""
    return Snapshot(
        framework_id=framework.id,
        framework_title=framework.title,
        created_at=created_at or _utcnow_iso(),
        metrics=metrics_to_jsonable(metrics),
        framework=model_to_jsonable(framework),
        units=model_to_jsonable(units),
        ontology=ontology_to_jsonable(ontology),
    )


class Store(Protocol):
    """Persistence seam. A Tirzah-backed store implements the same protocol."""

    def save(self, snapshot: Snapshot) -> str: ...
    def history(self, framework_id: str) -> list[Snapshot]: ...
    def load(self, framework_id: str, snapshot_id: str) -> Snapshot | None: ...


class JsonFileStore:
    """Dependency-free store: one JSON file per snapshot under
    `<root>/<framework_id>/<created_at>__<snapshot_id>.json`. History is the
    directory listing, ordered by `created_at`."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _dir(self, framework_id: str) -> Path:
        return self.root / framework_id

    def save(self, snapshot: Snapshot) -> str:
        d = self._dir(snapshot.framework_id)
        d.mkdir(parents=True, exist_ok=True)
        safe_ts = snapshot.created_at.replace(":", "").replace("-", "")
        path = d / f"{safe_ts}__{snapshot.snapshot_id}.json"
        path.write_text(json.dumps(snapshot.to_jsonable(), indent=2), encoding="utf-8")
        return snapshot.snapshot_id

    def history(self, framework_id: str) -> list[Snapshot]:
        d = self._dir(framework_id)
        if not d.exists():
            return []
        snaps = [Snapshot.from_jsonable(json.loads(p.read_text(encoding="utf-8")))
                 for p in d.glob("*.json")]
        return sorted(snaps, key=lambda s: s.created_at)

    def load(self, framework_id: str, snapshot_id: str) -> Snapshot | None:
        for snap in self.history(framework_id):
            if snap.snapshot_id == snapshot_id:
                return snap
        return None


def compute_trend(snapshots: list[Snapshot]) -> dict[str, Any]:
    """The movement of coherence metrics across snapshots (FR10 'trend over time').

    For each tracked metric: the time-ordered series and the first→last delta, so a
    framework that is improving (coherence up, fractures down) or degrading under
    pressure is visible. Empty/singleton histories yield zero deltas."""
    ordered = sorted(snapshots, key=lambda s: s.created_at)
    timeline = [s.created_at for s in ordered]
    series: dict[str, Any] = {}
    for metric in TREND_METRICS:
        values = [s.metrics.get(metric) for s in ordered]
        present = [v for v in values if isinstance(v, (int, float))]
        delta = (present[-1] - present[0]) if len(present) >= 2 else 0
        series[metric] = {"values": values, "delta": round(delta, 3)}
    return {"framework_id": ordered[0].framework_id if ordered else None,
            "count": len(ordered), "timeline": timeline, "metrics": series}
