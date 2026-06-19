"""Reasoning extraction (FR2).

Pull typed `ReasoningUnit`s out of a `Framework`. Two extractors sit behind one
`Extractor` interface, mirroring the sibling projects' adapter idiom:

- `RuleBasedExtractor` — deterministic, dependency-free, marker-based. The v0.2
  baseline: crude but transparent (every typing records the markers that produced
  it) and fully testable offline. It is the floor, not the ceiling.
- An LLM extractor — not a hard dependency here; `build_extraction_prompt` +
  `parse_extraction_response` are the seam an Ollama/Hoglah-backed extractor uses,
  kept separate from any model call so the prompt and parser are testable on their
  own (the same pattern Tirzah's deep-retrieval planner uses).

Dependencies (FR2) are emitted as edges: a bridge/conclusion unit `depends_on`
the unit it follows from.
"""

from __future__ import annotations

import json
import re
from typing import Protocol

from milcah.models import Framework, ReasoningUnit, ReasoningUnitType

# Marker phrases per type, in priority order (most distinctive first). A sentence
# is typed by the first type with a matching marker; unmatched sentences are
# claims. Markers are recorded on the unit as provenance.
_MARKER_RULES: list[tuple[ReasoningUnitType, tuple[str, ...]]] = [
    (ReasoningUnitType.CONCLUSION, (
        "in conclusion", "we conclude", "this proves", "therefore we", "ultimately",
        "in sum", "in summary", "we have shown",
    )),
    (ReasoningUnitType.OBSERVATION, (
        "we observe", "observed", "data show", "data shows", "evidence shows",
        "measured", "we see that", "empirically", "experiments show", "in practice",
    )),
    (ReasoningUnitType.ASSUMPTION, (
        "assume", "assuming", "suppose", "presuppose", "presupposes",
        "take for granted", "for the sake of argument", "let us grant",
    )),
    (ReasoningUnitType.PRIMITIVE, (
        "by definition", "axiom", "we take as given", "starting point",
        "first principle", "we posit", "taken as primitive",
    )),
    (ReasoningUnitType.COMMITMENT, (
        "must hold", "is required", "necessarily", "cannot be abandoned",
        "non-negotiable", "essential that", "has to be", "requires that",
    )),
    (ReasoningUnitType.ENTHYMEME, (
        "obviously", "clearly", "of course", "needless to say", "everyone knows",
        "self-evidently", "it goes without saying",
    )),
    (ReasoningUnitType.BRIDGE, (
        "therefore", "thus", "hence", "it follows", "which means", "consequently",
        "because", "so that", "this implies", "as a result",
    )),
]

# Bridge/conclusion units rest on what came before them.
_DEPENDENT_TYPES = {ReasoningUnitType.BRIDGE, ReasoningUnitType.CONCLUSION}

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def classify_sentence(sentence: str) -> tuple[ReasoningUnitType, list[str]]:
    """Return the (type, matched-markers) for one sentence."""
    lowered = sentence.lower()
    for unit_type, markers in _MARKER_RULES:
        hit = [m for m in markers if m in lowered]
        if hit:
            return unit_type, hit
    return ReasoningUnitType.CLAIM, []


class Extractor(Protocol):
    def extract(self, framework: Framework) -> list[ReasoningUnit]: ...


class RuleBasedExtractor:
    """Deterministic marker-based extraction — the transparent v0.2 baseline."""

    def extract(self, framework: Framework) -> list[ReasoningUnit]:
        units: list[ReasoningUnit] = []
        for segment in framework.segments:
            for sentence in split_sentences(segment.text):
                unit_type, markers = classify_sentence(sentence)
                unit = ReasoningUnit.make(
                    framework_id=framework.id,
                    unit_type=unit_type,
                    text=sentence,
                    segment_index=segment.index,
                    markers=markers,
                )
                # A bridge/conclusion rests on the immediately preceding unit.
                if unit_type in _DEPENDENT_TYPES and units:
                    unit.depends_on = [units[-1].id]
                units.append(unit)
        return units


def extract(framework: Framework, extractor: Extractor | None = None) -> list[ReasoningUnit]:
    """Extract reasoning units, defaulting to the deterministic baseline."""
    return (extractor or RuleBasedExtractor()).extract(framework)


# --------------------------------------------------------------------------- #
# LLM seam — prompt build + response parse, separate from any model call so both
# are testable. An Ollama/Hoglah-backed extractor calls a model between these.
# --------------------------------------------------------------------------- #

_VALID_TYPES = {t.value for t in ReasoningUnitType}


def build_extraction_prompt(framework: Framework, *, text: str | None = None) -> str:
    """Build the extraction prompt. By default it covers the whole framework; pass
    `text` (a single segment's text) to extract from just that excerpt — the basis
    of per-segment extraction."""
    type_list = ", ".join(t.value for t in ReasoningUnitType)
    body = text if text is not None else framework.raw_text
    scope = "EXCERPT of the framework" if text is not None else "FRAMEWORK"
    return (
        f"Extract the units of reasoning from the {scope} below. For each unit, "
        "give its type and its text.\n"
        f"Types (use exactly one per unit): {type_list}.\n"
        "Guidance: observation = an observed phenomenon; claim = a plain assertion; "
        "primitive = an accepted starting point; assumption = temporary support; "
        "commitment = required for the framework to survive; bridge = a mechanism "
        "connecting layers; enthymeme = an unstated/implied step; conclusion = a "
        "derived endpoint.\n\n"
        f"{scope} (framework title: {framework.title}):\n{body}\n\n"
        'Reply with ONLY a JSON array of objects like '
        '[{"type": "claim", "text": "..."}]. No prose.'
    )


def _extract_json_array(text: str):
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def parse_extraction_response(
    text: str, framework: Framework, *, segment_index: int | None = None
) -> list[ReasoningUnit]:
    """Parse an LLM extraction response into reasoning units (hostile input:
    malformed entries are skipped, unknown types dropped). `segment_index` tags
    the units with their source segment (and keeps their ids distinct across
    segments) when extracting per-segment."""
    data = _extract_json_array(text)
    if not isinstance(data, list):
        return []
    units: list[ReasoningUnit] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        raw_type = str(item.get("type", "")).strip().lower()
        unit_text = str(item.get("text", "")).strip()
        if raw_type not in _VALID_TYPES or not unit_text:
            continue
        units.append(
            ReasoningUnit.make(
                framework_id=framework.id,
                unit_type=ReasoningUnitType(raw_type),
                text=unit_text,
                segment_index=segment_index,
                markers=["llm"],
            )
        )
    return units
