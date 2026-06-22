"""Coherence metrics (FR7 / FR9).

Score a [worldview ontology](ontology.py) by **structure**, not by social signals.
Two families, kept separate:

- **Explanatory debt** (FR7) — what the framework leaves unpaid: assumption load,
  bridge load, unresolved load, dependency depth, and (when fallacy analysis has
  marked the ontology, FR6) located-fallacy load.
- **Coherence** (FR9) — global coherence, breadth, ontological completeness,
  fracture density, uncertainty burden.

Per the philosophy, these **deliberately exclude** popularity, confidence, and
institutional acceptance — and, here, also model-agreement / consensus (a
confidence-like signal): every number is computed purely from the ontology's
types, placement states, and shape. Deterministic and fully testable.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from milcah.models import ReasoningUnitType
from milcah.ontology import PlacementState, WorldviewOntology

_FOUNDATIONS = {ReasoningUnitType.OBSERVATION, ReasoningUnitType.PRIMITIVE}
_BRIDGES = {ReasoningUnitType.BRIDGE, ReasoningUnitType.ENTHYMEME}
_FRACTURES = {PlacementState.CONTRADICTORY_PLACEMENT, PlacementState.MULTIPLE_PLACEMENT_CANDIDATES}
_UNCERTAIN = {PlacementState.PARTIALLY_RESOLVED, PlacementState.DEPENDENT_ON_UNRESOLVED_BRIDGE}

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
    fallacy_load: int  # located logical fallacies (FR6), if marked onto the ontology
    # Coherence (FR9)
    global_coherence: float
    breadth: int
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


def compute_metrics(ontology: WorldviewOntology) -> CoherenceMetrics:
    """Compute the structural coherence metrics for an ontology (no social signals)."""
    nodes = list(ontology.nodes.values())
    n = len(nodes)
    if n == 0:
        return CoherenceMetrics(0, 0, 0, 0, 0, 0, 0.0, 0, 0.0, 0.0, 0.0)

    types = Counter(node.type for node in nodes)
    placements = Counter(node.placement for node in nodes)
    resolved = placements.get(PlacementState.RESOLVED, 0)
    fractures = sum(placements.get(p, 0) for p in _FRACTURES)
    uncertain = sum(placements.get(p, 0) for p in _UNCERTAIN)
    foundations = sum(types.get(t, 0) for t in _FOUNDATIONS)

    return CoherenceMetrics(
        node_count=n,
        assumption_load=types.get(ReasoningUnitType.ASSUMPTION, 0),
        bridge_load=sum(types.get(t, 0) for t in _BRIDGES),
        unresolved_load=n - resolved,
        dependency_depth=_max_depth(ontology),
        fallacy_load=sum(len(node.metadata.get("fallacies", [])) for node in nodes),
        global_coherence=round(resolved / n, 3),
        breadth=len(types),
        ontological_completeness=round(foundations / n, 3),
        fracture_density=round(fractures / n, 3),
        uncertainty_burden=round(uncertain / n, 3),
    )


def to_jsonable(metrics: CoherenceMetrics) -> dict[str, Any]:
    return asdict(metrics)
