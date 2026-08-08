"""Coherence metrics (FR7 / FR9).

Score a [worldview ontology](ontology.py) by **structure**, not by social signals.
Two families, kept separate:

- **Explanatory debt** (FR7) — what the framework leaves unpaid: assumption load,
  bridge load, unresolved load, dependency depth, and (when fallacy analysis has
  marked the ontology, FR6) located-fallacy load.
- **Coherence** (FR9) — global coherence, breadth, foundation ratio, fracture
  density, uncertainty burden.

Per the philosophy, these **deliberately exclude** popularity, confidence, and
institutional acceptance — and, here, also model-agreement / consensus (a
confidence-like signal): every number is computed purely from the ontology's
types, placement states, and shape. Deterministic and fully testable.

On the pure structural placement path (no LLM placement states),
``global_coherence`` is suppressed when every node is RESOLVED so a scaffold
ratio is not advertised as argument quality (review H1).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from milcah.models import ReasoningUnitType
from milcah.ontology import PlacementState, WorldviewOntology

_FOUNDATIONS = {ReasoningUnitType.OBSERVATION, ReasoningUnitType.PRIMITIVE}
_BRIDGES = {ReasoningUnitType.BRIDGE, ReasoningUnitType.ENTHYMEME}
_FRACTURES = {PlacementState.CONTRADICTORY_PLACEMENT, PlacementState.MULTIPLE_PLACEMENT_CANDIDATES}
_UNCERTAIN = {PlacementState.PARTIALLY_RESOLVED, PlacementState.DEPENDENT_ON_UNRESOLVED_BRIDGE}
# States that only an LLM / reasoned placement pass produces.
_REASONED_PLACEMENT = {
    PlacementState.MULTIPLE_PLACEMENT_CANDIDATES,
    PlacementState.CONTRADICTORY_PLACEMENT,
}

# Lightweight text hints so fallacy_load is not always 0 on the default metrics
# path (review M1). Full FR6 analysis still comes from `milcah fallacy`.
_FALLACY_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\banyone who disagrees\b", re.I), "ad_hominem"),
    (re.compile(r"\bhas not read the research\b", re.I), "ad_hominem"),
    (re.compile(r"\bfunded by\b", re.I), "poisoning_the_well"),
    (re.compile(r"\bobviously\b", re.I), "appeal_to_obviousness"),
    (re.compile(r"\bof course\b", re.I), "appeal_to_obviousness"),
    (re.compile(r"\beveryone knows\b", re.I), "appeal_to_popularity"),
    (re.compile(r"\bit follows that\b.*\btherefore\b", re.I), "non_sequitur"),
]

# Documented for honesty: signals that never enter a coherence score (philosophy).
EXCLUDED_SIGNALS = ("popularity", "confidence", "institutional_acceptance", "model_agreement")


@dataclass
class CoherenceMetrics:
    node_count: int
    # Explanatory debt (FR7)
    assumption_load: int
    bridge_load: int
    unresolved_load: int
    dependency_depth: int
    fallacy_load: int  # located logical fallacies (FR6) + structural hints
    # Coherence (FR9)
    # None when the structural scaffold would report a vacuous 1.0 (H1).
    global_coherence: float | None
    # Always resolved/n — what the structural path actually measures.
    structural_placement_ratio: float
    # True when no reasoned (LLM) placement states are present.
    placement_scaffold: bool
    breadth: int
    # Fraction of foundation-typed nodes (was misnamed ontological_completeness).
    foundation_ratio: float
    # Kept as an alias of foundation_ratio for API compatibility (L2).
    ontological_completeness: float
    fracture_density: float
    uncertainty_burden: float


def _max_depth(ontology: WorldviewOntology) -> int:
    nodes = ontology.nodes

    def depth(node_id: str, seen: frozenset[str]) -> int:
        if node_id in seen:  # guard against any accidental cycle
            return 0
        children = nodes[node_id].children
        return 1 + max((depth(c, seen | {node_id}) for c in children), default=0)

    return max((depth(r, frozenset()) for r in ontology.roots), default=0)


def _text_fallacy_hints(text: str) -> list[str]:
    return [name for pattern, name in _FALLACY_HINTS if pattern.search(text or "")]


def compute_metrics(ontology: WorldviewOntology) -> CoherenceMetrics:
    """Compute the structural coherence metrics for an ontology (no social signals)."""
    nodes = list(ontology.nodes.values())
    n = len(nodes)
    if n == 0:
        return CoherenceMetrics(
            0, 0, 0, 0, 0, 0, 0.0, 0.0, True, 0, 0.0, 0.0, 0.0, 0.0
        )

    types = Counter(node.type for node in nodes)
    placements = Counter(node.placement for node in nodes)
    resolved = placements.get(PlacementState.RESOLVED, 0)
    fractures = sum(placements.get(p, 0) for p in _FRACTURES)
    uncertain = sum(placements.get(p, 0) for p in _UNCERTAIN)
    foundations = sum(types.get(t, 0) for t in _FOUNDATIONS)
    ratio = round(resolved / n, 3)
    scaffold = sum(placements.get(p, 0) for p in _REASONED_PLACEMENT) == 0
    # Vacuous perfect score on pure structural placement is not "coherence".
    if scaffold and resolved == n:
        global_coherence: float | None = None
    else:
        global_coherence = ratio

    marked = sum(len(node.metadata.get("fallacies", []) or []) for node in nodes)
    hinted = sum(len(_text_fallacy_hints(getattr(node, "text", "") or "")) for node in nodes)

    foundation_ratio = round(foundations / n, 3)
    return CoherenceMetrics(
        node_count=n,
        assumption_load=types.get(ReasoningUnitType.ASSUMPTION, 0),
        bridge_load=sum(types.get(t, 0) for t in _BRIDGES),
        unresolved_load=n - resolved,
        dependency_depth=_max_depth(ontology),
        fallacy_load=marked + hinted,
        global_coherence=global_coherence,
        structural_placement_ratio=ratio,
        placement_scaffold=scaffold,
        breadth=len(types),
        foundation_ratio=foundation_ratio,
        ontological_completeness=foundation_ratio,
        fracture_density=round(fractures / n, 3),
        uncertainty_burden=round(uncertain / n, 3),
    )


def to_jsonable(metrics: CoherenceMetrics) -> dict[str, Any]:
    data = asdict(metrics)
    # JSON-friendly null for suppressed global_coherence
    return data
