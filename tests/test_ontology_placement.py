import json

from milcah.models import ReasoningUnit, ReasoningUnitType as RT
from milcah.ontology import PlacementState as PS, build_ontology
from milcah.ontology_placement import (
    build_placement_prompt,
    parse_placement_response,
    refine_placement,
)


def _onto():
    fid = "f"
    units = [
        ReasoningUnit.make(framework_id=fid, unit_type=RT.OBSERVATION, text="A is observed"),
        ReasoningUnit.make(framework_id=fid, unit_type=RT.CONCLUSION, text="therefore B"),
    ]
    return build_ontology(fid, units)


def test_build_placement_prompt_lists_nodes_and_states():
    o = _onto()
    prompt = build_placement_prompt(o)
    assert "contradictory_placement" in prompt and "resolved" in prompt
    assert "JSON object" in prompt
    for nid in o.nodes:
        assert nid[:8] in prompt  # short ids the model replies with


def test_parse_placement_response_valid_and_filtered():
    o = _onto()
    ids = [nid[:8] for nid in o.nodes]
    full = list(o.nodes)
    raw = "noise " + json.dumps(
        {ids[0]: "contradictory_placement", ids[1]: "bogus_state", "deadbeef": "resolved"}
    ) + " noise"
    out = parse_placement_response(raw, o)
    assert out[full[0]] == PS.CONTRADICTORY_PLACEMENT
    assert full[1] not in out  # invalid state dropped
    assert len(out) == 1  # unknown id ("deadbeef") ignored


def test_parse_placement_handles_non_json():
    assert parse_placement_response("no json here", _onto()) == {}


def test_refine_placement_applies_and_marks_source():
    o = _onto()
    full = list(o.nodes)

    def fake_submit(prompt, model):
        assert "JSON object" in prompt and model == "m"
        return json.dumps({full[0][:8]: "contradictory_placement"})

    refined = refine_placement(o, submit=fake_submit, model="m")
    assert refined.nodes[full[0]].placement == PS.CONTRADICTORY_PLACEMENT
    assert refined.nodes[full[0]].metadata["placement_source"] == "llm"
    # a node the model omitted keeps its structural placement
    assert refined.nodes[full[1]].placement == PS.RESOLVED
    assert "placement_source" not in refined.nodes[full[1]].metadata
