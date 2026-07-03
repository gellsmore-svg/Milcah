"""Galeed coherence-run tracing (milcah.tracing) — optional, best-effort spine witness."""

from __future__ import annotations

import pytest

pytest.importorskip("galeed", reason="galeed extra not installed")

from milcah.ingestion import ingest_text
from milcah.models import ReasoningUnit, ReasoningUnitType
from milcah.orchestration import orchestrate
from milcah.tracing import (
    ORCHESTRATION_COMPLETED,
    ORCHESTRATION_STARTED,
    SNAPSHOT_SAVED,
    Witness,
    set_witness,
)


class FakeCollection:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def insert_one(self, doc: dict) -> None:
        self.rows.append(doc)


class FakeDb:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections.setdefault(name, FakeCollection())


def _events(fake: FakeDb) -> list[dict]:
    return fake.collections.get("trace_events", FakeCollection()).rows


@pytest.fixture(autouse=True)
def _reset_witness():
    yield
    set_witness(None)


def test_disabled_by_default_emits_nothing() -> None:
    fake = FakeDb()
    witness = Witness(enabled=False, db=fake)
    witness.emit(SNAPSHOT_SAVED, trace_id="s1", summary="quiet")
    assert _events(fake) == []


def test_env_enablement(monkeypatch) -> None:
    monkeypatch.setenv("MILCAH_GALEED_ENABLED", "1")
    assert Witness(db=FakeDb()).enabled
    monkeypatch.delenv("MILCAH_GALEED_ENABLED")
    assert not Witness(db=FakeDb()).enabled


def test_orchestrate_emits_started_and_completed() -> None:
    fake = FakeDb()
    set_witness(Witness(enabled=True, db=fake))

    framework = ingest_text("All humans are mortal. Socrates is human.", title="Syllogism")
    units = [
        ReasoningUnit.make(
            framework_id=framework.id,
            unit_type=ReasoningUnitType.CLAIM,
            text="all humans are mortal",
        ),
    ]
    orchestrate(
        framework,
        units,
        expand=lambda prompt, model: "",
        challenge=lambda prompt, model: "",
        analyse=lambda prompt, model: "",
    )

    rows = _events(fake)
    types = [row["type"] for row in rows]
    assert types == [ORCHESTRATION_STARTED, ORCHESTRATION_COMPLETED]
    assert all(row["source"] == "milcah" for row in rows)
    # Both events share one trace: a single orchestration run.
    assert rows[0]["trace_id"] == rows[1]["trace_id"]
    assert rows[1]["metadata"]["framework_id"] == framework.id


def test_witness_never_raises_on_broken_db() -> None:
    class ExplodingDb:
        def __getitem__(self, name):
            raise RuntimeError("no db for you")

    witness = Witness(enabled=True, db=ExplodingDb())
    witness.emit(SNAPSHOT_SAVED, trace_id="s1", summary="resilient")  # must not raise
