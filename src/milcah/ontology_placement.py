"""LLM-driven ontological placement (FR3, the reasoned step).

The deterministic [scaffold](ontology.py) places nodes from structure + agreement
signals; this asks a model to *reason* about placement — review the worldview tree
and assign each node a placement state, including the one the scaffold reserves:
**contradictory_placement** (a node that conflicts with another it should cohere
with). It is the bridge toward Mahalath's debated placement.

The prompt build + response parse are pure and separate from the model call (the
same seam as extraction), so they are testable on their own. `refine_placement`
applies an injectable `submit(prompt, model) -> output`; `make_placement_runner`
wires it through Hoglah.
"""

from __future__ import annotations

import json
from typing import Callable

from milcah.hoglah_extractor import HoglahExtractorConfig, make_hoglah_submitter
from milcah.ontology import PlacementState, WorldviewOntology

_VALID = {p.value for p in PlacementState}
_SHORT = 8  # short id length shown to the model


def build_placement_prompt(ontology: WorldviewOntology) -> str:
    nodes = []
    for nid, n in ontology.nodes.items():
        rests_on = ontology.nodes[n.parent_id].text[:60] if n.parent_id else "(root / foundation)"
        nodes.append({"id": nid[:_SHORT], "type": n.type.value, "text": n.text[:160], "rests_on": rests_on})
    states = ", ".join(p.value for p in PlacementState)
    return (
        "You are placing the nodes of a worldview ontology. For each node, assign "
        "exactly one ontological placement state.\n"
        f"States: {states}.\n"
        "Definitions: resolved = well-supported and internally consistent; "
        "partially_resolved = support is incomplete or left implicit; "
        "multiple_placement_candidates = it could reasonably sit in more than one place; "
        "dependent_on_unresolved_bridge = it rests on an unestablished connecting step; "
        "contradictory_placement = it conflicts with another node it should cohere with.\n\n"
        "Nodes (a node 'rests_on' its support):\n" + json.dumps(nodes, indent=2) + "\n\n"
        'Reply with ONLY a JSON object mapping each id to one placement state, e.g. '
        '{"a1b2c3d4": "resolved"}. No prose.'
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


def parse_placement_response(text: str, ontology: WorldviewOntology) -> dict[str, PlacementState]:
    """Parse an LLM placement response into {node_id: PlacementState} (hostile
    input: unknown ids and invalid states are dropped)."""
    data = _extract_json_object(text)
    if not isinstance(data, dict):
        return {}
    short_to_id = {nid[:_SHORT]: nid for nid in ontology.nodes}
    out: dict[str, PlacementState] = {}
    for short, value in data.items():
        node_id = short_to_id.get(str(short))
        state = str(value).strip().lower()
        if node_id and state in _VALID:
            out[node_id] = PlacementState(state)
    return out


def refine_placement(
    ontology: WorldviewOntology, *, submit: Callable[[str, str], str], model: str
) -> WorldviewOntology:
    """Run the LLM placement pass and apply it in place. Nodes the model places get
    their `placement` updated and `metadata['placement_source'] = 'llm'`; nodes it
    omits keep their structural scaffold placement."""
    output = submit(build_placement_prompt(ontology), model)
    for node_id, placement in parse_placement_response(output, ontology).items():
        node = ontology.nodes[node_id]
        node.placement = placement
        node.metadata["placement_source"] = "llm"
    return ontology


def make_placement_runner(config: HoglahExtractorConfig) -> Callable[[str, str], str]:
    """A `submit(prompt, model) -> output` runner through Hoglah for placement."""
    submitter = make_hoglah_submitter(config)

    def run(prompt: str, model: str) -> str:
        return submitter.run(prompt, model)

    return run
