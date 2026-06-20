import json

from milcah.models import ReasoningUnit, ReasoningUnitType as RT
from milcah.ontology import PlacementState as PS, build_ontology
from milcah.recursive import (
    QUESTIONS,
    build_reasoning_prompt,
    parse_reasoning_response,
    recurse_reasoning,
)


def _onto(text="root claim"):
    fid = "f"
    return build_ontology(fid, [ReasoningUnit.make(framework_id=fid, unit_type=RT.CLAIM, text=text)])


def test_build_reasoning_prompt_lists_questions_and_claim():
    o = _onto()
    node = next(iter(o.nodes.values()))
    prompt = build_reasoning_prompt(node)
    for key in QUESTIONS:
        assert key in prompt
    assert "root claim" in prompt and "JSON object" in prompt


def test_parse_reasoning_response_filters_and_tags():
    raw = json.dumps(
        {
            "supports": [{"type": "observation", "text": "obs"}],
            "implies": [{"type": "conclusion", "text": "c"}],
            "bogus_relation": [{"type": "claim", "text": "x"}],
            "assumptions": [{"type": "not_a_type", "text": "y"}],
        }
    )
    units = parse_reasoning_response(raw, "f", source_node_id="n1")
    assert sorted(u.metadata["relation"] for u in units) == ["implies", "supports"]
    assert all(u.metadata["source_node"] == "n1" and u.metadata["generated"] for u in units)
    assert all("generated" in u.markers for u in units)


def test_recurse_respects_depth_threshold():
    o = _onto()
    calls = []

    def expand(node, framework_id):
        calls.append(node.id)
        return [
            ReasoningUnit.make(framework_id=framework_id, unit_type=RT.OBSERVATION, text=f"{node.id[:6]}-{i}")
            for i in range(2)
        ]

    res = recurse_reasoning(o, expand=expand, max_depth=1, max_new_nodes=10)
    assert res.generated == 2
    assert len(calls) == 1  # only the depth-0 root is expanded
    children = [n for n in res.ontology.nodes.values() if n.parent_id is not None]
    assert len(children) == 2
    assert all(c.placement == PS.PARTIALLY_RESOLVED and c.metadata["depth"] == 1 for c in children)


def test_recurse_respects_node_budget():
    o = _onto()

    def expand(node, framework_id):
        return [
            ReasoningUnit.make(framework_id=framework_id, unit_type=RT.CLAIM, text=f"{node.id[:6]}-{i}")
            for i in range(5)
        ]

    res = recurse_reasoning(o, expand=expand, max_depth=5, max_new_nodes=3)
    assert res.generated == 3
    assert res.stop_reason == "node_budget"


def test_recurse_goes_two_levels_deep():
    o = _onto()

    def expand(node, framework_id):
        return [ReasoningUnit.make(framework_id=framework_id, unit_type=RT.CLAIM, text=f"{node.id[:6]}-child")]

    res = recurse_reasoning(o, expand=expand, max_depth=2, max_new_nodes=10)
    # root(d0) -> child(d1) -> grandchild(d2); grandchild not expanded (d2 >= max_depth)
    assert res.generated == 2
    depths = sorted(n.metadata.get("depth", 0) for n in res.ontology.nodes.values() if n.parent_id)
    assert depths == [1, 2]
