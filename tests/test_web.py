"""Snapshot viewer (milcah.web) — read-only FR10 browser over the Store seam."""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi", reason="web extra not installed")

from fastapi.testclient import TestClient  # noqa: E402

from milcah.persistence import JsonFileStore, Snapshot  # noqa: E402
from milcah.web import create_app  # noqa: E402


def _snap(created_at: str, coherence: float, fractures: float) -> Snapshot:
    return Snapshot(
        framework_id="fw1",
        framework_title="Test Worldview",
        created_at=created_at,
        metrics={
            "global_coherence": coherence,
            "fracture_density": fractures,
            "node_count": 5,
        },
        units=[{"unit_type": "claim", "text": "c1"}, {"unit_type": "assumption", "text": "a1"}],
        framework={"id": "fw1", "title": "Test Worldview"},
        ontology={"nodes": []},
    )


@pytest.fixture()
def store(tmp_path):
    s = JsonFileStore(tmp_path / "snapshots")
    s.save(_snap("2026-06-23T10:00:00Z", 0.5, 0.4))
    s.save(_snap("2026-06-24T10:00:00Z", 0.7, 0.2))
    return s


@pytest.fixture()
def client(store):
    return TestClient(create_app(store, store_label="test-store"))


def test_frameworks_listing(store) -> None:
    rows = store.frameworks()
    assert len(rows) == 1
    assert rows[0]["framework_id"] == "fw1"
    assert rows[0]["snapshot_count"] == 2
    assert rows[0]["latest_metrics"]["global_coherence"] == 0.7


def test_index_page(client) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "Test Worldview" in r.text
    assert "fw1" in r.text


def test_framework_trend_page(client) -> None:
    r = client.get("/frameworks/fw1")
    assert r.status_code == 200
    assert "global_coherence" in r.text
    assert "<svg" in r.text  # sparkline rendered
    assert "delta-good" in r.text  # coherence up + fractures down both improve


def test_snapshot_detail_page(client, store) -> None:
    snapshot_id = store.history("fw1")[-1].snapshot_id
    r = client.get(f"/frameworks/fw1/snapshots/{snapshot_id}")
    assert r.status_code == 200
    assert "claim: 1" in r.text
    assert "assumption: 1" in r.text


def test_api_routes(client, store) -> None:
    assert client.get("/api/frameworks").json()["frameworks"][0]["framework_id"] == "fw1"
    trend = client.get("/api/frameworks/fw1/trend").json()["trend"]
    assert trend["count"] == 2
    assert trend["metrics"]["global_coherence"]["delta"] == pytest.approx(0.2)
    snapshot_id = store.history("fw1")[-1].snapshot_id
    snap = client.get(f"/api/frameworks/fw1/snapshots/{snapshot_id}").json()["snapshot"]
    assert snap["snapshot_id"] == snapshot_id


def test_missing_framework_and_snapshot_404(client) -> None:
    assert client.get("/frameworks/nope").status_code == 404
    assert client.get("/frameworks/fw1/snapshots/nope").status_code == 404
    assert client.get("/api/frameworks/nope/trend").status_code == 404


def test_invalid_framework_id_is_400(client) -> None:
    assert client.get("/api/frameworks/.hidden/trend").status_code == 400
    assert client.get("/api/frameworks/.hidden/snapshots/abc").status_code == 400
