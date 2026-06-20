from milcah.extraction import extract
from milcah.ingestion import ingest_text
from milcah.models import ReasoningUnit, ReasoningUnitType as RT
from milcah.ontology import PlacementState as PS, build_ontology, to_jsonable


def _u(fid, t, text, depends_on=None, metadata=None):
    u = ReasoningUnit.make(framework_id=fid, unit_type=t, text=text, metadata=metadata)
    if depends_on:
        u.depends_on = depends_on
    return u


def test_build_ontology_structural_tree_by_tier():
    fid = "f"
    obs = _u(fid, RT.OBSERVATION, "particles persist")
    asm = _u(fid, RT.ASSUMPTION, "identity is topological")
    con = _u(fid, RT.CONCLUSION, "matter is topology")
    o = build_ontology(fid, [obs, asm, con])

    # foundation is a root; each later unit attaches to the nearest more-foundational one
    assert o.roots == [obs.id]
    assert o.nodes[asm.id].parent_id == obs.id
    assert o.nodes[con.id].parent_id == asm.id
    assert o.nodes[obs.id].children == [asm.id]
    assert o.nodes[obs.id].placement == PS.RESOLVED  # observation = foundation


def test_explicit_depends_on_takes_precedence_and_bridge_dependence():
    fid = "f"
    claim = _u(fid, RT.CLAIM, "X holds")
    bridge = _u(fid, RT.BRIDGE, "therefore Y", depends_on=[claim.id])
    concl = _u(fid, RT.CONCLUSION, "Z", depends_on=[bridge.id])
    o = build_ontology(fid, [claim, bridge, concl])

    assert o.nodes[bridge.id].parent_id == claim.id
    assert o.nodes[concl.id].parent_id == bridge.id
    # resting on a (bridge) mechanism -> dependent on unresolved bridge
    assert o.nodes[concl.id].placement == PS.DEPENDENT_ON_UNRESOLVED_BRIDGE


def test_scaffold_placement_is_structural_not_agreement_based():
    # model-agreement signals (type_votes / consensus) do NOT drive the structural
    # scaffold — those richer states come from the reasoned LLM placement pass.
    fid = "f"
    u = _u(fid, RT.CLAIM, "X", metadata={"type_votes": {"claim": 2, "assumption": 1}, "consensus": 0.2})
    o = build_ontology(fid, [u])
    assert o.nodes[u.id].placement == PS.RESOLVED


def test_placement_partially_resolved_for_enthymeme():
    fid = "f"
    enth = _u(fid, RT.ENTHYMEME, "obviously it follows")
    o = build_ontology(fid, [enth])
    assert o.nodes[enth.id].placement == PS.PARTIALLY_RESOLVED


def test_scaffold_only_assigns_structural_states():
    fid = "f"
    units = [_u(fid, t, f"u{t.value}") for t in RT]
    o = build_ontology(fid, units)
    structural = {PS.RESOLVED, PS.PARTIALLY_RESOLVED, PS.DEPENDENT_ON_UNRESOLVED_BRIDGE}
    assert all(n.placement in structural for n in o.nodes.values())


def test_render_and_jsonable():
    fid = "f"
    o = build_ontology(fid, [_u(fid, RT.OBSERVATION, "base"), _u(fid, RT.CONCLUSION, "top")])
    rendered = o.render()
    assert "base" in rendered and "top" in rendered

    d = to_jsonable(o)
    assert d["framework_id"] == fid
    assert isinstance(d["nodes"], dict)
    assert all(isinstance(n["placement"], str) and isinstance(n["type"], str) for n in d["nodes"].values())


def test_build_ontology_from_extracted_units():
    fw = ingest_text("We observe that X happens. Therefore Y follows.", title="t")
    units = extract(fw)  # rule-based; the bridge depends_on the preceding unit
    o = build_ontology(fw.id, units)
    assert len(o.nodes) == len(units)
    assert len(o.roots) >= 1
    assert all(n.id in o.nodes for n in o.nodes.values())
