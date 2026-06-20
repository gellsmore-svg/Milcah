"""Ontology construction (FR3) — the worldview tree.

Turn a framework's [reasoning units](models.py) into a **worldview ontology**: a
tree of nodes (foundations at the root, derived claims branching out) where each
node carries an **ontological placement state** from `docs/philosophy.md`
(resolved … contradictory).

This is the v1 **structural scaffold**: it is deterministic and testable, built
from the units' types, order, explicit `depends_on` edges, and the multi-LLM
agreement signals already on each unit. Placement here is *structural* — the
philosophy's full placement (debated, contradiction-aware) is LLM/Mahalath work,
the natural next step. `CONTRADICTORY_PLACEMENT` is therefore reserved for that
later reasoning pass and never assigned by this scaffold.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from milcah.models import ReasoningUnit, ReasoningUnitType


class PlacementState(str, Enum):
    """Ontological placement states (docs/philosophy.md)."""

    RESOLVED = "resolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    MULTIPLE_PLACEMENT_CANDIDATES = "multiple_placement_candidates"
    DEPENDENT_ON_UNRESOLVED_BRIDGE = "dependent_on_unresolved_bridge"
    CONTRADICTORY_PLACEMENT = "contradictory_placement"  # reserved for the LLM/debate pass


# Foundational → derived tiers: where a unit type sits in a worldview's support
# structure. Lower tier = more foundational (a support for what is above it).
_TIER: dict[ReasoningUnitType, int] = {
    ReasoningUnitType.OBSERVATION: 0,
    ReasoningUnitType.PRIMITIVE: 0,
    ReasoningUnitType.ASSUMPTION: 1,
    ReasoningUnitType.COMMITMENT: 1,
    ReasoningUnitType.CLAIM: 1,
    ReasoningUnitType.BRIDGE: 2,
    ReasoningUnitType.ENTHYMEME: 2,
    ReasoningUnitType.CONCLUSION: 3,
}

_FOUNDATIONS = {ReasoningUnitType.OBSERVATION, ReasoningUnitType.PRIMITIVE}
_BRIDGES = {ReasoningUnitType.BRIDGE, ReasoningUnitType.ENTHYMEME}


@dataclass
class OntologyNode:
    id: str
    unit_id: str
    type: ReasoningUnitType
    text: str
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)
    placement: PlacementState = PlacementState.RESOLVED
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldviewOntology:
    framework_id: str
    nodes: dict[str, OntologyNode] = field(default_factory=dict)
    roots: list[str] = field(default_factory=list)

    def render(self) -> str:
        """An indented tree view (foundations at the root)."""
        lines: list[str] = []

        def walk(node_id: str, depth: int) -> None:
            n = self.nodes[node_id]
            lines.append(f"{'  ' * depth}- [{n.type.value}/{n.placement.value}] {n.text[:60]}")
            for child in n.children:
                walk(child, depth + 1)

        for root in self.roots:
            walk(root, 0)
        return "\n".join(lines)


def build_ontology(framework_id: str, units: list[ReasoningUnit]) -> WorldviewOntology:
    """Build the worldview tree from reasoning units (deterministic scaffold)."""
    nodes = {
        u.id: OntologyNode(
            id=u.id, unit_id=u.id, type=u.type, text=u.text, metadata=dict(u.metadata or {})
        )
        for u in units
    }

    # Parent = what a unit rests on. Prefer an explicit depends_on edge; otherwise
    # attach to the nearest *preceding*, *more foundational* unit (lower tier).
    for index, u in enumerate(units):
        parent_id = _explicit_parent(u, nodes) or _structural_parent(units, index)
        if parent_id and parent_id != u.id:
            nodes[u.id].parent_id = parent_id
            nodes[parent_id].children.append(u.id)

    roots = [u.id for u in units if nodes[u.id].parent_id is None]

    for node in nodes.values():
        node.placement = _placement(node, nodes)

    return WorldviewOntology(framework_id=framework_id, nodes=nodes, roots=roots)


def _explicit_parent(unit: ReasoningUnit, nodes: dict[str, OntologyNode]) -> str | None:
    for dep in unit.depends_on:
        if dep in nodes:
            return dep
    return None


def _structural_parent(units: list[ReasoningUnit], index: int) -> str | None:
    tier = _TIER.get(units[index].type, 1)
    # the closest preceding unit that is strictly more foundational
    for j in range(index - 1, -1, -1):
        if _TIER.get(units[j].type, 1) < tier:
            return units[j].id
    return None


def _placement(node: OntologyNode, nodes: dict[str, OntologyNode]) -> PlacementState:
    type_votes = node.metadata.get("type_votes")
    if isinstance(type_votes, dict) and len(type_votes) > 1:
        # the models disagreed on what this unit *is*
        return PlacementState.MULTIPLE_PLACEMENT_CANDIDATES
    if node.parent_id and nodes[node.parent_id].type in _BRIDGES:
        # it rests on an (unestablished) connecting mechanism
        return PlacementState.DEPENDENT_ON_UNRESOLVED_BRIDGE
    if node.type == ReasoningUnitType.ENTHYMEME:
        return PlacementState.PARTIALLY_RESOLVED
    consensus = node.metadata.get("consensus")
    if isinstance(consensus, (int, float)) and consensus < 0.5:
        # weak multi-LLM agreement → not firmly placed
        return PlacementState.PARTIALLY_RESOLVED
    return PlacementState.RESOLVED


def to_jsonable(value: Any) -> Any:
    """JSON-serialisable view of an ontology (or node)."""
    if isinstance(value, (WorldviewOntology, OntologyNode)):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    return value
