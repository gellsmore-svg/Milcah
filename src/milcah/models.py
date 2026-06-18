"""Core data model for Milcah's first stage: ingestion (FR1) and reasoning
extraction (FR2).

Two records carry the work:

- `Framework` — a normalised, segmented input (a book, document, hypothesis,
  argument tree, conversation, web research, or structured ontology).
- `ReasoningUnit` — a typed unit of reasoning pulled out of a framework. The
  types are faithful to `docs/philosophy.md` ("Assumptions Must Become Visible":
  primitive / assumption / commitment / bridge / enthymeme) plus FR2's
  observations / claims / conclusions. Dependencies (FR2) are modelled as edges
  between units (`depends_on`), not a unit type.

Ids are deterministic content hashes so re-ingesting the same input yields the
same ids — idempotent storage and stable test assertions.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class SourceType(str, Enum):
    """The kinds of input a framework can be ingested from (FR1)."""

    DOCUMENT = "document"
    BOOK = "book"
    HYPOTHESIS = "hypothesis"
    ARGUMENT_TREE = "argument_tree"
    CONVERSATION = "conversation"
    WEB = "web"
    STRUCTURED_ONTOLOGY = "structured_ontology"


class ReasoningUnitType(str, Enum):
    """Typed units of reasoning (FR2 + philosophy "Assumptions Must Become Visible")."""

    OBSERVATION = "observation"  # an observed phenomenon; precedes frameworks
    CLAIM = "claim"  # a declarative assertion the framework makes
    PRIMITIVE = "primitive"  # an accepted starting point
    ASSUMPTION = "assumption"  # temporary support
    COMMITMENT = "commitment"  # required for the framework's survival
    BRIDGE = "bridge"  # a mechanism connecting layers
    ENTHYMEME = "enthymeme"  # an unstated reasoning structure
    CONCLUSION = "conclusion"  # a derived endpoint


def _hash(*parts: str) -> str:
    digest = hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


@dataclass
class Segment:
    """A normalised chunk of a framework (a paragraph / turn / node)."""

    index: int
    text: str


@dataclass
class Framework:
    """A normalised, segmented input ready for reasoning extraction."""

    id: str
    title: str
    source_type: SourceType
    raw_text: str
    segments: list[Segment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def make(
        cls,
        *,
        title: str,
        source_type: SourceType,
        raw_text: str,
        segments: list[Segment] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Framework:
        return cls(
            id=_hash("framework", title, raw_text),
            title=title,
            source_type=source_type,
            raw_text=raw_text,
            segments=segments or [],
            metadata=metadata or {},
        )


@dataclass
class ReasoningUnit:
    """A typed unit of reasoning extracted from a framework."""

    id: str
    framework_id: str
    type: ReasoningUnitType
    text: str
    segment_index: int | None = None
    depends_on: list[str] = field(default_factory=list)  # ids of units this rests on
    markers: list[str] = field(default_factory=list)  # provenance: why it was typed so
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def make(
        cls,
        *,
        framework_id: str,
        unit_type: ReasoningUnitType,
        text: str,
        segment_index: int | None = None,
        markers: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ReasoningUnit:
        return cls(
            id=_hash("unit", framework_id, str(segment_index), text),
            framework_id=framework_id,
            type=unit_type,
            text=text,
            segment_index=segment_index,
            markers=markers or [],
            metadata=metadata or {},
        )


def to_jsonable(value: Any) -> Any:
    """Convert a model (or list of models) into JSON-serialisable plain data."""
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (Framework, Segment, ReasoningUnit)):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, Enum):
        return value.value
    return value
