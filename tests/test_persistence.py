from milcah.extraction import RuleBasedExtractor, extract
from milcah.ingestion import ingest_text
from milcah.metrics import compute_metrics
from milcah.ontology import build_ontology
from milcah.persistence import (
    JsonFileStore,
    Snapshot,
    build_snapshot,
    compute_trend,
)


def _analyse(text, title="F"):
    fw = ingest_text(text, title=title)
    units = extract(fw, RuleBasedExtractor())
    onto = build_ontology(fw.id, units)
    return fw, units, onto, compute_metrics(onto)


def test_build_snapshot_captures_the_analysis():
    fw, units, onto, metrics = _analyse("Space is discrete. Therefore time is discrete.")
    snap = build_snapshot(fw, units, onto, metrics, created_at="2026-06-23T10:00:00Z")
    assert snap.framework_id == fw.id and snap.framework_title == "F"
    assert snap.metrics["global_coherence"] == metrics.global_coherence
    assert snap.ontology["framework_id"] == fw.id
    assert len(snap.units) == len(units)
    assert snap.snapshot_id  # deterministic id present


def test_jsonfilestore_roundtrip_and_history(tmp_path):
    store = JsonFileStore(tmp_path)
    fw, units, onto, metrics = _analyse("A primitive. A claim rests on it.")
    s1 = build_snapshot(fw, units, onto, metrics, created_at="2026-06-23T10:00:00Z")
    s2 = build_snapshot(fw, units, onto, metrics, created_at="2026-06-23T12:00:00Z")

    id1 = store.save(s1)
    store.save(s2)

    hist = store.history(fw.id)
    assert [s.created_at for s in hist] == ["2026-06-23T10:00:00Z", "2026-06-23T12:00:00Z"]
    loaded = store.load(fw.id, id1)
    assert loaded is not None and loaded.created_at == "2026-06-23T10:00:00Z"
    assert loaded.metrics == s1.metrics


def test_history_unknown_framework_is_empty(tmp_path):
    assert JsonFileStore(tmp_path).history("nope") == []
    assert JsonFileStore(tmp_path).load("nope", "x") is None


def test_compute_trend_tracks_metric_movement():
    # Two snapshots of the same framework with coherence improving over time.
    a = Snapshot(framework_id="f", framework_title="F", created_at="2026-06-23T10:00:00Z",
                 metrics={"global_coherence": 0.5, "fracture_density": 0.4, "node_count": 4})
    b = Snapshot(framework_id="f", framework_title="F", created_at="2026-06-23T12:00:00Z",
                 metrics={"global_coherence": 0.8, "fracture_density": 0.1, "node_count": 6})
    trend = compute_trend([b, a])  # deliberately unordered
    assert trend["count"] == 2
    assert trend["timeline"] == ["2026-06-23T10:00:00Z", "2026-06-23T12:00:00Z"]
    assert trend["metrics"]["global_coherence"]["values"] == [0.5, 0.8]
    assert trend["metrics"]["global_coherence"]["delta"] == 0.3   # improved
    assert trend["metrics"]["fracture_density"]["delta"] == -0.3  # fewer fractures


def test_compute_trend_singleton_has_zero_delta():
    a = Snapshot(framework_id="f", framework_title="F", created_at="t",
                 metrics={"global_coherence": 0.5})
    trend = compute_trend([a])
    assert trend["metrics"]["global_coherence"]["delta"] == 0
