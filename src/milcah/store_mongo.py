"""MongoDB-backed snapshot store (FR10) — the family's shared persistence layer.

The optional, durable backend for [persistence](persistence.py). It writes
[snapshots](persistence.py) to a dedicated `snapshots` collection in the **shared
MongoDB the family uses** (where Tirzah's `mnemosyne_dev` and Mahalath's
`mahalath_dev` also live) — so Milcah's coherence history sits alongside the rest of
the family's memory.

Milcah's analysis snapshots are structured blobs, not graph memory, so they get
their own collection rather than being forced through Tirzah's node ingestion. This
implements the same `Store` protocol as `JsonFileStore`; `pymongo` is an **optional
dependency** (the `mongo` extra) imported lazily, so Milcah's core stays
dependency-free.
"""

from __future__ import annotations

from typing import Any

from milcah.persistence import Snapshot


class MongoStore:
    """A `Store` over a MongoDB collection. Construct with `make_mongo_store` (real)
    or pass any collection-like object (tests). Idempotent on `snapshot_id`."""

    def __init__(self, collection: Any) -> None:
        self._col = collection

    def save(self, snapshot: Snapshot) -> str:
        doc = snapshot.to_jsonable()
        doc["_id"] = snapshot.snapshot_id
        self._col.replace_one({"_id": doc["_id"]}, doc, upsert=True)
        return snapshot.snapshot_id

    def history(self, framework_id: str) -> list[Snapshot]:
        docs = list(self._col.find({"framework_id": framework_id}))
        snaps = [Snapshot.from_jsonable(d) for d in docs]
        return sorted(snaps, key=lambda s: s.created_at)

    def load(self, framework_id: str, snapshot_id: str) -> Snapshot | None:
        doc = self._col.find_one({"_id": snapshot_id, "framework_id": framework_id})
        return Snapshot.from_jsonable(doc) if doc else None


def make_mongo_store(
    uri: str = "mongodb://localhost:27017",
    database: str = "milcah_dev",
    collection: str = "snapshots",
) -> MongoStore:
    """Build a MongoStore against the shared MongoDB (lazy `pymongo` import)."""
    from pymongo import MongoClient

    client = MongoClient(uri)
    return MongoStore(client[database][collection])
