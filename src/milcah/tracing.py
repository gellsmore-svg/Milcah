"""Optional Galeed trace emission — witness coherence runs on the family spine.

When enabled, Milcah testifies its analysis lifecycle onto the shared trace
stream: an orchestration run starting/completing and snapshots being saved.
Event types are Milcah-domain extensions of Galeed's open vocabulary
(``orchestration.started``, ``orchestration.completed``, ``snapshot.saved``);
the generic ``job.*`` set stays with infrastructure (Hoglah).

Milcah's core is dependency-free and has no config file, so enablement is
environment-driven:

    MILCAH_GALEED_ENABLED=1
    MILCAH_GALEED_MONGO_URI=mongodb://localhost:27017   (default)
    MILCAH_GALEED_MONGO_DB=mnemosyne_dev                (default)

pointing at the database the family trace API (Tirzah ``/api/trace``, Mizpah)
reads. Strictly best-effort and optional: ``galeed`` (the ``galeed`` extra) and
``pymongo`` are imported lazily, and every failure is swallowed — tracing must
never affect an analysis.
"""

from __future__ import annotations

import atexit
import logging
import os
import threading
from typing import Any

logger = logging.getLogger("milcah")

ORCHESTRATION_STARTED = "orchestration.started"
ORCHESTRATION_COMPLETED = "orchestration.completed"
SNAPSHOT_SAVED = "snapshot.saved"

_TRUTHY = {"1", "true", "yes", "on"}


class Witness:
    """Best-effort emitter of coherence-run events onto the Galeed spine."""

    def __init__(self, enabled: bool | None = None, db: Any = None) -> None:
        if enabled is None:
            enabled = os.environ.get("MILCAH_GALEED_ENABLED", "").lower() in _TRUTHY
        self._enabled = enabled
        self._db = db
        self._db_resolved = db is not None
        self._db_lock = threading.Lock()
        # Only set when this witness opened the connection itself — an injected
        # db belongs to the caller and must never be closed from here.
        self._client: Any = None
        self._atexit_registered = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _database(self) -> Any:
        # Locked, resolved-flag-last: concurrent first emissions from different
        # threads must never observe a half-initialised handle (a None here
        # silently drops events).
        with self._db_lock:
            if self._db_resolved:
                return self._db
            try:
                from pymongo import MongoClient

                client = MongoClient(
                    os.environ.get("MILCAH_GALEED_MONGO_URI", "mongodb://localhost:27017"),
                    serverSelectionTimeoutMS=2000,
                )
                self._client = client
                self._db = client[os.environ.get("MILCAH_GALEED_MONGO_DB", "mnemosyne_dev")]
                if not self._atexit_registered:
                    # Tracing is lazy and process-wide, so nothing else is
                    # guaranteed to close this. atexit runs while the
                    # interpreter is still healthy, giving an orderly close.
                    atexit.register(self.close)
                    self._atexit_registered = True
            except Exception:
                logger.debug("galeed trace db unavailable; emitting bus-only", exc_info=True)
                self._db = None
            self._db_resolved = True
            return self._db

    def close(self) -> None:
        """Close the MongoClient this witness opened; no-op for an injected db.

        Safe to call repeatedly and from atexit. A later emit simply re-resolves
        a fresh connection, so closing early is never fatal to tracing.
        """
        with self._db_lock:
            client, self._client = self._client, None
            if client is not None:
                self._db = None
                self._db_resolved = False
        if client is not None:
            try:
                client.close()
            except Exception:
                logger.debug("closing galeed trace client failed (ignored)", exc_info=True)

    def emit(
        self,
        type: str,
        *,
        trace_id: str,
        status: str = "completed",
        summary: str = "",
        session_id: str = "milcah",
        **metadata: Any,
    ) -> None:
        """Emit one lifecycle event; swallows every failure by design."""
        if not self._enabled:
            return
        try:
            from galeed import Tracer
        except ImportError:
            self._enabled = False
            logger.debug("galeed not installed; coherence-run tracing disabled")
            return
        try:
            tracer = Tracer(
                trace_id=trace_id,
                session_id=session_id,
                db=self._database(),
                source="milcah",
            )
            tracer.emit(type, status=status, summary=summary, **metadata)
        except Exception:
            logger.debug("galeed emit failed (ignored)", exc_info=True)


_witness: Witness | None = None


def get_witness() -> Witness:
    """Process-wide witness (env-configured). Tests replace it via set_witness()."""
    global _witness
    if _witness is None:
        _witness = Witness()
    return _witness


def set_witness(witness: Witness | None) -> None:
    """Override (or reset with None) the process-wide witness — for tests."""
    global _witness
    previous, _witness = _witness, witness
    if previous is not None and previous is not witness:
        previous.close()  # only closes a connection it opened itself
