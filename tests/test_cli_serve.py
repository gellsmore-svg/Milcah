"""`milcah serve` store lifecycle (#15).

The viewer opens an FR10 store (a real MongoClient under `--store mongo`) and
must close it when the server stops — including on Ctrl-C, which is how a serve
session normally ends.
"""

from __future__ import annotations

import argparse
import sys
import types

import pytest

fastapi = pytest.importorskip("fastapi", reason="web extra not installed")

from milcah import cli  # noqa: E402


class FakeStore:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1

    def history(self, framework_id: str):
        return []

    def frameworks(self):
        return []


def _serve_args() -> argparse.Namespace:
    return argparse.Namespace(host="127.0.0.1", port=8791, store="json", store_dir="unused")


def _stub_uvicorn(monkeypatch, run) -> None:
    module = types.ModuleType("uvicorn")
    module.run = run  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "uvicorn", module)


def test_serve_closes_the_store_on_normal_shutdown(monkeypatch) -> None:
    store = FakeStore()
    monkeypatch.setattr(cli, "_open_store", lambda args: (store, "fake-store"))
    _stub_uvicorn(monkeypatch, lambda *args, **kwargs: None)

    assert cli._cmd_serve(_serve_args()) == 0
    assert store.closed == 1


def test_serve_closes_the_store_on_ctrl_c(monkeypatch) -> None:
    """The common exit path: uvicorn propagates KeyboardInterrupt."""
    store = FakeStore()
    monkeypatch.setattr(cli, "_open_store", lambda args: (store, "fake-store"))

    def _boom(*args, **kwargs):
        raise KeyboardInterrupt

    _stub_uvicorn(monkeypatch, _boom)

    with pytest.raises(KeyboardInterrupt):
        cli._cmd_serve(_serve_args())
    assert store.closed == 1


def test_close_store_tolerates_stores_without_close() -> None:
    """JsonFileStore holds no connection and has no close()."""
    cli._close_store(object())  # must not raise
