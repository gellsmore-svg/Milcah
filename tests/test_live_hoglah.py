"""Opt-in live Hoglah extraction path (review F5).

Gated behind RUN_HOGLAH_TESTS=1 so default CI stays offline and fast.
"""

from __future__ import annotations

import os

import pytest

requires_hoglah = pytest.mark.skipif(
    os.environ.get("RUN_HOGLAH_TESTS") != "1",
    reason="Live Hoglah tests require RUN_HOGLAH_TESTS=1 and a running worker.",
)


@requires_hoglah
def test_hoglah_extractor_returns_units() -> None:
    from milcah.extraction import extract
    from milcah.hoglah_extractor import HoglahExtractor, HoglahExtractorConfig
    from milcah.ingestion import ingest_text

    fw = ingest_text(
        "We assume space is continuous. Therefore topology preserves identity.",
        title="live-hoglah",
    )
    units = extract(fw, HoglahExtractor(HoglahExtractorConfig()))
    assert units  # at least one unit from the model path
