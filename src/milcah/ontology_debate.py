"""Delegate ontology debate to Mahalath (FR3 — the family ontology authority).

Milcah builds the *structure* of a worldview (the [ontology](ontology.py) tree and
its [placement states](ontology.py)). But whether a given **term** is ontologically
well-grounded — a single clean sense, several co-equal senses (polysemy), or a
stale/contested definition — is exactly what **Mahalath** (the multi-agent ontology
builder) debates. This module delegates that judgment: for each node, ask Mahalath
about the term, and let its debated ontology *inform placement*.

Faithful to Milcah's stance, the delegation can only **expose** fractures, never
resolve one away (Milcah pressure-tests). Mahalath's verdict moves a node DOWN the
coherence ladder or leaves it:
  - polysemous (multiple senses) -> `multiple_placement_candidates`;
  - stale/contested term         -> `partially_resolved`;
  - cleanly grounded / unknown   -> unchanged.

The resolver is an injectable callable (pure + testable offline);
`make_mahalath_debater` is the real backend over Mahalath's ontology — `mahalath`
+ `pymongo` are optional (the `mahalath` extra), imported lazily, so Milcah's core
stays dependency-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from milcah.ontology import PlacementState, WorldviewOntology


@dataclass
class MahalathPlacement:
    """Mahalath's debated view of a term: its MPL grounding + how settled it is."""

    term: str
    mpl_label: str
    senses: list[str] = field(default_factory=list)  # Mahalath "frames" / meaning contexts
    is_stale: bool = False
    match_kind: str = ""


# A resolver maps a node's text to Mahalath's verdict on its key term (or None).
ResolveFn = Callable[[str], "MahalathPlacement | None"]

# Coherence severity — debate may only move a node to a worse (higher) state.
_SEVERITY: dict[PlacementState, int] = {
    PlacementState.RESOLVED: 0,
    PlacementState.PARTIALLY_RESOLVED: 1,
    PlacementState.DEPENDENT_ON_UNRESOLVED_BRIDGE: 1,
    PlacementState.MULTIPLE_PLACEMENT_CANDIDATES: 2,
    PlacementState.CONTRADICTORY_PLACEMENT: 3,
}


def _worse(a: PlacementState, b: PlacementState) -> PlacementState:
    return a if _SEVERITY.get(a, 0) >= _SEVERITY.get(b, 0) else b


def _implied(placement: MahalathPlacement) -> PlacementState:
    if len(placement.senses) > 1:
        return PlacementState.MULTIPLE_PLACEMENT_CANDIDATES  # polysemy — co-equal senses
    if placement.is_stale:
        return PlacementState.PARTIALLY_RESOLVED  # contested / upstream changed
    return PlacementState.RESOLVED  # cleanly grounded — no worsening


def debate_placement(ontology: WorldviewOntology, resolve: ResolveFn) -> int:
    """Let Mahalath's debated ontology inform each node's placement (in place).

    Returns the number of nodes Mahalath had a verdict on. Each such node gains
    `metadata['mahalath']` (the MPL label + senses) and, where Mahalath exposes a
    weaker grounding, a worsened placement tagged `placement_source='mahalath'`.
    """
    informed = 0
    for node in ontology.nodes.values():
        verdict = resolve(node.text)
        if verdict is None or not verdict.mpl_label:
            continue
        informed += 1
        node.metadata["mahalath"] = {
            "mpl_label": verdict.mpl_label,
            "term": verdict.term,
            "senses": verdict.senses,
            "is_stale": verdict.is_stale,
        }
        implied = _implied(verdict)
        worsened = _worse(node.placement, implied)
        if worsened != node.placement:
            node.placement = worsened
            node.metadata["placement_source"] = "mahalath"
    return informed


def make_mahalath_debater(
    uri: str = "mongodb://localhost:27017",
    database: str = "mahalath_dev",
    language: str = "en",
    timeout_ms: int = 2000,
) -> ResolveFn:
    """A resolver over Mahalath's ontology (`mahalath.retrieval.search_terms`).

    Optional + fail-soft: if `mahalath`/`pymongo` aren't installed or the store is
    unreachable, every lookup returns None and placement is simply not informed.
    """
    try:
        from pymongo import MongoClient

        from mahalath.retrieval import Filters, search_terms
    except Exception:
        return lambda _text: None

    try:
        db = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)[database]
    except Exception:
        return lambda _text: None
    filters = Filters(language=language)

    def resolve(text: str) -> MahalathPlacement | None:
        try:
            matches = search_terms(db, [text], filters=filters, limit=1)
        except Exception:
            return None
        if not matches:
            return None
        m = matches[0]
        return MahalathPlacement(
            term=m.canonical_term, mpl_label=m.mpl_label,
            senses=list(m.frames), is_stale=m.is_stale, match_kind=m.match_kind,
        )

    return resolve


def to_jsonable(value: Any) -> Any:
    if isinstance(value, MahalathPlacement):
        return {"term": value.term, "mpl_label": value.mpl_label,
                "senses": value.senses, "is_stale": value.is_stale, "match_kind": value.match_kind}
    return value
