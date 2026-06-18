"""Framework ingestion (FR1).

Normalise an input — text, a file, a conversation, a structured argument — into a
`Framework`: a titled record with the raw text preserved and a list of trimmed
`Segment`s (the units later stages reason over).

The v0.2 baseline segments on blank-line-separated paragraphs (and, for
conversations, speaker turns). Richer per-source parsing (argument trees, web
research, structured ontology) layers on later behind the same entry points; the
`source_type` is always recorded so downstream stages can specialise.
"""

from __future__ import annotations

import re
from pathlib import Path

from milcah.models import Framework, Segment, SourceType

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
# A conversation turn like "Alice: ..." / "> Bob: ...".
_TURN_PREFIX = re.compile(r"^\s*>?\s*([A-Z][\w .'-]{0,40}):\s")


def segment_text(text: str, *, source_type: SourceType = SourceType.DOCUMENT) -> list[Segment]:
    """Split normalised text into trimmed, non-empty segments."""
    if source_type == SourceType.CONVERSATION:
        raw_parts = _split_conversation(text)
    else:
        raw_parts = _PARAGRAPH_SPLIT.split(text)
    segments: list[Segment] = []
    for part in raw_parts:
        cleaned = " ".join(part.split())
        if cleaned:
            segments.append(Segment(index=len(segments), text=cleaned))
    return segments


def _split_conversation(text: str) -> list[str]:
    """One segment per speaker turn; lines without a speaker join the prior turn."""
    turns: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if _TURN_PREFIX.match(line) or not turns:
            turns.append(line.strip())
        else:
            turns[-1] = f"{turns[-1]} {line.strip()}"
    return turns


def ingest_text(
    text: str,
    *,
    title: str | None = None,
    source_type: SourceType = SourceType.DOCUMENT,
    metadata: dict | None = None,
) -> Framework:
    """Normalise raw text into a segmented `Framework`."""
    resolved_title = (title or _derive_title(text) or "untitled framework").strip()
    return Framework.make(
        title=resolved_title,
        source_type=source_type,
        raw_text=text,
        segments=segment_text(text, source_type=source_type),
        metadata=metadata or {},
    )


def ingest_file(
    path: str | Path,
    *,
    source_type: SourceType | None = None,
    title: str | None = None,
    metadata: dict | None = None,
) -> Framework:
    """Read a file and ingest it. `source_type` defaults by extension."""
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    resolved_type = source_type or _source_type_for(file_path)
    meta = {"source_path": str(file_path), **(metadata or {})}
    return ingest_text(
        text,
        title=title or file_path.stem.replace("_", " ").replace("-", " "),
        source_type=resolved_type,
        metadata=meta,
    )


def _derive_title(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:120]
    return None


def _source_type_for(path: Path) -> SourceType:
    suffix = path.suffix.lower()
    if suffix in {".json", ".yaml", ".yml"}:
        return SourceType.STRUCTURED_ONTOLOGY
    return SourceType.DOCUMENT
