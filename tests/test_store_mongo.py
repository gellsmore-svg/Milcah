"""MongoStore tests — hermetic, via a minimal fake collection (no live Mongo)."""

from milcah.persistence import Snapshot
from milcah.store_mongo import MongoStore


class _FakeCollection:
    """Just enough of a pymongo collection for MongoStore."""

    def __init__(self):
        self.docs: dict[str, dict] = {}

    def replace_one(self, flt, doc, upsert=False):
        self.docs[flt["_id"]] = dict(doc)

    def find(self, query):
        return [d for d in self.docs.values()
                if all(d.get(k) == v for k, v in query.items())]

    def find_one(self, query):
        for d in self.docs.values():
            if all(d.get(k) == v for k, v in query.items()):
                return d
        return None


def _snap(fid, ts, coherence=0.5):
    return Snapshot(framework_id=fid, framework_title="F", created_at=ts,
                    metrics={"global_coherence": coherence})


def test_save_history_load_roundtrip():
    store = MongoStore(_FakeCollection())
    a = _snap("f1", "2026-06-23T10:00:00Z", 0.5)
    b = _snap("f1", "2026-06-23T12:00:00Z", 0.8)
    other = _snap("f2", "2026-06-23T11:00:00Z")
    ida = store.save(a); store.save(b); store.save(other)

    hist = store.history("f1")
    assert [s.created_at for s in hist] == ["2026-06-23T10:00:00Z", "2026-06-23T12:00:00Z"]
    assert store.history("f2")[0].framework_id == "f2"  # isolated by framework
    loaded = store.load("f1", ida)
    assert loaded is not None and loaded.metrics["global_coherence"] == 0.5


def test_save_is_idempotent_on_snapshot_id():
    col = _FakeCollection()
    store = MongoStore(col)
    s = _snap("f1", "2026-06-23T10:00:00Z")
    store.save(s); store.save(s)  # same id (framework_id + created_at)
    assert len(col.docs) == 1
    assert len(store.history("f1")) == 1


def test_load_missing_returns_none():
    store = MongoStore(_FakeCollection())
    assert store.load("f1", "nope") is None
    assert store.history("f1") == []
