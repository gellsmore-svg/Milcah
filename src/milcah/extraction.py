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

Marker matching (review H2): word-boundary anchors, earliest-in-sentence wins
across types, and a short negation window rejects inverted markers.
"""

from __future__ import annotations

import json
import re
from typing import Protocol

from milcah.models import Framework, ReasoningUnit, ReasoningUnitType

# Marker phrases per type. Matching is no longer "first list wins": we score by
# earliest character position in the sentence (review H2).
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

# Discourse markers that only count near sentence start (avoid "clearly printed").
_INITIAL_REQUIRED = {
    "therefore", "thus", "hence", "consequently", "in conclusion", "in sum",
    "in summary", "ultimately", "as a result", "it follows", "obviously",
    "clearly", "of course", "needless to say", "everyone knows", "self-evidently",
    "it goes without saying", "because", "so that",
}

# Negation tokens that invert a following marker (window of ~4 words).
_NEGATION = re.compile(
    r"\b(not|never|no|n't|cannot|can't|don't|doesn't|didn't|isn't|aren't|"
    r"wasn't|weren't|without|hardly|rarely|neither)\b",
    re.I,
)

# Abbreviations / initials that should not end a sentence (review H3).
_ABBREV = {
    "dr", "mr", "mrs", "ms", "prof", "sr", "jr", "st", "ave", "fig", "eq",
    "eqs", "vol", "no", "nos", "pp", "p", "cf", "vs", "etc", "al", "eg", "ie",
    "approx", "dept", "univ", "ed", "eds", "rev", "gen", "lt", "col", "sgt",
}


def _marker_pattern(marker: str) -> re.Pattern[str]:
    # Word-boundary-ish: multi-word phrases get flexible whitespace.
    parts = [re.escape(p) for p in marker.split()]
    body = r"\s+".join(parts)
    return re.compile(rf"(?<![\w]){body}(?![\w])", re.I)


_COMPILED: list[tuple[ReasoningUnitType, str, re.Pattern[str]]] = [
    (unit_type, marker, _marker_pattern(marker))
    for unit_type, markers in _MARKER_RULES
    for marker in markers
]


def _negated_at(lowered: str, match_start: int) -> bool:
    """True if a negation appears in a short window before the match."""
    window = lowered[max(0, match_start - 40) : match_start]
    # Last ~4 tokens in the window.
    tokens = re.findall(r"[a-z']+", window)
    tail = tokens[-4:] if tokens else []
    return any(_NEGATION.fullmatch(t) for t in tail)


def split_sentences(text: str) -> list[str]:
    """Split on sentence boundaries without fracturing common abbreviations (H3)."""
    if not text or not text.strip():
        return []
    # Protect known abbreviations and single-letter initials (e.g. "J. Smith").
    protected = text
    placeholders: list[str] = []

    def _hold(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return f"\x00{len(placeholders) - 1}\x00"

    # Multi-dot Latin abbreviations first (e.g. / i.e.).
    protected = re.sub(r"\b([Ee]\.[Gg]\.|[Ii]\.[Ee]\.)", _hold, protected)
    # Fig. / Dr. / p. / single initials
    protected = re.sub(
        r"\b([A-Za-z]{1,12})\.(?=\s|$)",
        lambda m: _hold(m) if m.group(1).lower().rstrip(".") in _ABBREV or (
            len(m.group(1)) == 1 and m.group(1).isalpha()
        ) else m.group(0),
        protected,
    )
    # Also protect "e.g." / "i.e." written with internal dots already partially handled.

    parts = re.split(r"(?<=[.!?])\s+", protected)
    out: list[str] = []
    for part in parts:
        restored = part
        for i, original in enumerate(placeholders):
            restored = restored.replace(f"\x00{i}\x00", original)
        cleaned = restored.strip()
        if cleaned:
            out.append(cleaned)
    return out


def classify_sentence(sentence: str) -> tuple[ReasoningUnitType, list[str]]:
    """Return the (type, matched-markers) for one sentence.

    Earliest non-negated word-boundary match wins across all types (H2).
    """
    lowered = sentence.lower()
    best: tuple[int, int, ReasoningUnitType, str] | None = None
    # best = (start, -length preference for longer phrases, type, marker)
    for unit_type, marker, pattern in _COMPILED:
        for m in pattern.finditer(lowered):
            if _negated_at(lowered, m.start()):
                continue
            start = m.start()
            # Discourse markers only when little/no prose precedes them (H2).
            if marker in _INITIAL_REQUIRED:
                prefix = lowered[:start].strip()
                if prefix and prefix not in {"and", "but", "so", "yet", "for", "thus"}:
                    continue
            key = (start, -len(marker), unit_type.value, marker)
            if best is None or key < (best[0], best[1], best[2].value, best[3]):
                best = (start, -len(marker), unit_type, marker)
    if best is None:
        return ReasoningUnitType.CLAIM, []
    return best[2], [best[3]]


def strip_markdown_noise(text: str) -> str:
    """Drop heading markers, list bullets, and fenced code for extraction (M2)."""
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Headings / bullets / blockquotes → keep the prose only.
        stripped = re.sub(r"^#{1,6}\s+", "", stripped)
        stripped = re.sub(r"^[-*+]\s+", "", stripped)
        stripped = re.sub(r"^\d+\.\s+", "", stripped)
        stripped = re.sub(r"^>\s?", "", stripped)
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)


class Extractor(Protocol):
    def extract(self, framework: Framework) -> list[ReasoningUnit]: ...


class RuleBasedExtractor:
    """Deterministic marker-based extraction — the transparent v0.2 baseline."""

    def extract(self, framework: Framework) -> list[ReasoningUnit]:
        units: list[ReasoningUnit] = []
        for segment in framework.segments:
            prose = strip_markdown_noise(segment.text)
            for sentence in split_sentences(prose):
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
