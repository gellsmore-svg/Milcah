"""Recursive reasoner (FR4) — the five questions.

For each node in the [worldview ontology](ontology.py), ask the five questions of
Milcah's recursive pressure-testing — *what supports this? what must be true? what
does this imply? what assumptions does it rest on? what explains those
assumptions?* — generating new typed [reasoning units](models.py) that attach to
the node and expand the tree. Recursion is **bounded** (FR11): a depth threshold
and a new-node budget guarantee termination.

The prompt build + response parse are pure and testable (the LLM seam); the
recursion control (`recurse_reasoning`) is deterministic given an injectable
`expand(node) -> units`; `make_hoglah_reasoner` runs the questions through Hoglah.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from milcah.hoglah_extractor import HoglahExtractorConfig, make_hoglah_submitter
from milcah.models import ReasoningUnit, ReasoningUnitType
from milcah.ontology import OntologyNode, PlacementState, WorldviewOntology
from milcah.web_research import WebResearchClient, render_research_evidence, sources_to_jsonable

# The five questions, keyed by the relation each answer bears to the source node.
QUESTIONS: dict[str, str] = {
    "supports": "what supports this?",
    "must_be_true": "what must be true for this to hold?",
    "implies": "what does this imply?",
    "assumptions": "what assumptions does it rest on?",
    "explains": "what explains those assumptions?",
}

_VALID_TYPES = {t.value for t in ReasoningUnitType}


@dataclass
class ReasoningResult:
    ontology: WorldviewOntology
    generated: int = 0
    expanded_nodes: int = 0
    stop_reason: str = ""
    trace: list[dict[str, Any]] = field(default_factory=list)


def build_reasoning_prompt(node: OntologyNode, research_evidence: str | None = None) -> str:
    type_list = ", ".join(t.value for t in ReasoningUnitType)
    questions = "\n".join(f"- {key}: {q}" for key, q in QUESTIONS.items())
    return (
        "Pressure-test the claim below by answering five questions. For each, give "
        "zero or more typed reasoning units (a type and its text).\n"
        f"Claim [{node.type.value}]: {node.text}\n\n"
        f"Questions (answer each):\n{questions}\n\n"
        f"Types (use exactly one per unit): {type_list}.\n\n"
        + ((research_evidence + "\n\n") if research_evidence else "")
        + 'Reply with ONLY a JSON object whose keys are the five question keys and '
        'whose values are arrays of {"type": ..., "text": ...}, e.g. '
        '{"supports": [{"type": "observation", "text": "..."}], "must_be_true": [], '
        '"implies": [], "assumptions": [], "explains": []}. No prose.'
    )


def _extract_json_object(text: str):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def parse_reasoning_response(
    text: str, framework_id: str, *, source_node_id: str | None = None,
    research_sources: list[dict[str, Any]] | None = None,
) -> list[ReasoningUnit]:
    """Parse a five-question response into new reasoning units, each tagged with
    the `relation` (which question produced it) and its source node. Hostile
    input: unknown relations/types and malformed entries are skipped."""
    data = _extract_json_object(text)
    if not isinstance(data, dict):
        return []
    units: list[ReasoningUnit] = []
    for relation, items in data.items():
        if relation not in QUESTIONS or not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            raw_type = str(item.get("type", "")).strip().lower()
            unit_text = str(item.get("text", "")).strip()
            if raw_type not in _VALID_TYPES or not unit_text:
                continue
            units.append(
                ReasoningUnit.make(
                    framework_id=framework_id,
                    unit_type=ReasoningUnitType(raw_type),
                    text=unit_text,
                    markers=["generated", relation],
                    metadata={"relation": relation, "source_node": source_node_id, "generated": True, **({"research_sources": research_sources} if research_sources else {})},
                )
            )
    return units


ExpandFn = Callable[[OntologyNode, str], list[ReasoningUnit]]


def recurse_reasoning(
    ontology: WorldviewOntology,
    *,
    expand: ExpandFn,
    max_depth: int = 1,
    max_new_nodes: int = 12,
) -> ReasoningResult:
    """Expand the ontology by recursively asking the five questions of each node.

    Breadth-first from the existing nodes (depth 0). Each `expand(node)` returns new
    units that become child nodes (placement = partially_resolved — generated, not
    yet established). Terminates on the new-node **budget** or the **depth**
    threshold (FR11), whichever comes first; guaranteed to stop.
    """
    result = ReasoningResult(ontology=ontology)
    queue: list[tuple[str, int]] = [(nid, 0) for nid in list(ontology.nodes)]
    while queue:
        if result.generated >= max_new_nodes:
            result.stop_reason = "node_budget"
            break
        node_id, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        source = ontology.nodes[node_id]
        new_units = expand(source, ontology.framework_id) or []
        kept = 0
        for unit in new_units:
            if result.generated >= max_new_nodes:
                break
            if unit.id in ontology.nodes:  # dedup: a unit already in the tree
                continue
            ontology.nodes[unit.id] = OntologyNode(
                id=unit.id,
                unit_id=unit.id,
                type=unit.type,
                text=unit.text,
                parent_id=node_id,
                placement=PlacementState.PARTIALLY_RESOLVED,
                metadata={**(unit.metadata or {}), "depth": depth + 1},
            )
            source.children.append(unit.id)
            queue.append((unit.id, depth + 1))
            result.generated += 1
            kept += 1
        result.expanded_nodes += 1
        result.trace.append({"node": node_id[:8], "depth": depth, "generated": kept})
    if not result.stop_reason:
        result.stop_reason = "exhausted"
    return result


def make_hoglah_reasoner(
    config: HoglahExtractorConfig, research: WebResearchClient | None = None
) -> ExpandFn:
    """An `expand(node) -> units` that asks the five questions through Hoglah."""
    submitter = make_hoglah_submitter(config)
    model = config.model

    def expand(node: OntologyNode, framework_id: str) -> list[ReasoningUnit]:
        sources = research.research(node.text) if research else []
        evidence = render_research_evidence(node.text, sources) if sources else None
        output = submitter.run(build_reasoning_prompt(node, evidence), model)
        return parse_reasoning_response(
            output, framework_id, source_node_id=node.id,
            research_sources=sources_to_jsonable(sources) if sources else None,
        )

    return expand
