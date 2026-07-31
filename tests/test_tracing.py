"""Galeed coherence-run tracing (milcah.tracing) — optional, best-effort spine witness."""

from __future__ import annotations

import sys
import types

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


def test_close_shuts_the_client_it_opened(monkeypatch) -> None:
    """The lazy MongoClient must be closable rather than leaked (#17)."""
    closed: list[bool] = []

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __getitem__(self, name):
            return FakeDb()

        def close(self) -> None:
            closed.append(True)

    fake_pymongo = types.ModuleType("pymongo")
    fake_pymongo.MongoClient = FakeClient  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pymongo", fake_pymongo)

    witness = Witness(enabled=True)
    assert witness._database() is not None  # resolves and opens the client
    witness.close()
    assert closed == [True]

    witness.close()  # idempotent — nothing left to close
    assert closed == [True]


def test_close_does_not_touch_an_injected_db() -> None:
    """An injected db belongs to the caller; close() must leave it usable."""
    fake = FakeDb()
    witness = Witness(enabled=True, db=fake)

    witness.close()

    witness.emit(SNAPSHOT_SAVED, trace_id="s1", summary="still writing")
    assert [row["type"] for row in _events(fake)] == [SNAPSHOT_SAVED]


def test_set_witness_closes_the_one_it_replaces(monkeypatch) -> None:
    closed: list[str] = []

    class Recording(Witness):
        def close(self) -> None:
            closed.append("closed")
            super().close()

    first = Recording(enabled=False)
    set_witness(first)
    set_witness(None)
    assert closed == ["closed"]
