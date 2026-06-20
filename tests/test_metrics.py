from milcah.metrics import EXCLUDED_SIGNALS, compute_metrics
from milcah.models import ReasoningUnit, ReasoningUnitType as RT
from milcah.ontology import OntologyNode, PlacementState as PS, WorldviewOntology, build_ontology


def _ont(nodes_spec):
    """nodes_spec: list of (id, type, placement, parent_id)."""
    nodes = {}
    roots = []
    for nid, t, placement, parent in nodes_spec:
        nodes[nid] = OntologyNode(id=nid, unit_id=nid, type=t, text=nid, parent_id=parent, placement=placement)
        if parent is None:
            roots.append(nid)
    for nid, _, _, parent in nodes_spec:
        if parent is not None:
            nodes[parent].children.append(nid)
    return WorldviewOntology(framework_id="f", nodes=nodes, roots=roots)


def test_metrics_on_empty_ontology():
    m = compute_metrics(WorldviewOntology(framework_id="f"))
    assert m.node_count == 0 and m.global_coherence == 0.0


def test_metrics_counts_and_ratios():
    o = _ont([
        ("obs", RT.OBSERVATION, PS.RESOLVED, None),
        ("asm", RT.ASSUMPTION, PS.PARTIALLY_RESOLVED, "obs"),
        ("brg", RT.BRIDGE, PS.DEPENDENT_ON_UNRESOLVED_BRIDGE, "asm"),
        ("con", RT.CONCLUSION, PS.CONTRADICTORY_PLACEMENT, "brg"),
        ("clm", RT.CLAIM, PS.MULTIPLE_PLACEMENT_CANDIDATES, "obs"),
    ])
    m = compute_metrics(o)
    assert m.node_count == 5
    # explanatory debt
    assert m.assumption_load == 1
    assert m.bridge_load == 1  # one bridge (enthymeme would also count)
    assert m.unresolved_load == 4  # only obs is resolved
    assert m.dependency_depth == 4  # obs -> asm -> brg -> con
    # coherence
    assert m.global_coherence == round(1 / 5, 3)
    assert m.breadth == 5  # five distinct types present
    assert m.ontological_completeness == round(1 / 5, 3)  # one foundation (obs)
    assert m.fracture_density == round(2 / 5, 3)  # contradictory + multiple-candidates
    assert m.uncertainty_burden == round(2 / 5, 3)  # partially + dependent-on-bridge


def test_metrics_exclude_social_signals():
    # multi-LLM agreement metadata must NOT change the structural metrics
    fid = "f"
    u1 = ReasoningUnit.make(framework_id=fid, unit_type=RT.OBSERVATION, text="x", metadata={"agreement": 3, "consensus": 1.0})
    u2 = ReasoningUnit.make(framework_id=fid, unit_type=RT.OBSERVATION, text="y", metadata={"agreement": 1, "consensus": 0.1})
    a = compute_metrics(build_ontology(fid, [u1]))
    b = compute_metrics(build_ontology(fid, [u2]))
    assert a == b  # agreement/consensus differ, metrics identical
    assert "model_agreement" in EXCLUDED_SIGNALS and "popularity" in EXCLUDED_SIGNALS


def test_metrics_from_built_ontology_all_resolved():
    o = build_ontology("f", [ReasoningUnit.make(framework_id="f", unit_type=RT.OBSERVATION, text="a foundation")])
    m = compute_metrics(o)
    assert m.global_coherence == 1.0 and m.fracture_density == 0.0 and m.ontological_completeness == 1.0
