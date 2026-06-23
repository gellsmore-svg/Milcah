from milcah.models import ReasoningUnitType as RT
from milcah.ontology import OntologyNode, PlacementState as PS, WorldviewOntology
from milcah.ontology_debate import MahalathPlacement, debate_placement


def _ont(specs):
    """specs: list of (id, text, placement)."""
    nodes = {nid: OntologyNode(id=nid, unit_id=nid, type=RT.CLAIM, text=text, placement=pl)
             for nid, text, pl in specs}
    return WorldviewOntology(framework_id="f", nodes=nodes, roots=list(nodes))


def _resolver(table):
    """table: substring -> MahalathPlacement; first containing match wins."""
    def resolve(text):
        for key, placement in table.items():
            if key in text:
                return placement
        return None
    return resolve


def test_polysemy_becomes_multiple_candidates():
    ont = _ont([("n1", "the substrate underlies everything", PS.RESOLVED)])
    resolve = _resolver({"substrate": MahalathPlacement(
        term="substrate", mpl_label="MPL-902", senses=["structural", "physical"])})
    informed = debate_placement(ont, resolve)
    n = ont.nodes["n1"]
    assert informed == 1
    assert n.placement is PS.MULTIPLE_PLACEMENT_CANDIDATES   # co-equal senses
    assert n.metadata["mahalath"]["mpl_label"] == "MPL-902"
    assert n.metadata["placement_source"] == "mahalath"


def test_stale_term_downgrades_resolved_to_partial():
    ont = _ont([("n1", "the form holds", PS.RESOLVED)])
    resolve = _resolver({"form": MahalathPlacement(
        term="form", mpl_label="MPL-904", senses=["structural"], is_stale=True)})
    debate_placement(ont, resolve)
    assert ont.nodes["n1"].placement is PS.PARTIALLY_RESOLVED


def test_clean_grounding_leaves_placement_but_annotates():
    ont = _ont([("n1", "the vorton spins", PS.RESOLVED)])
    resolve = _resolver({"vorton": MahalathPlacement(
        term="vorton", mpl_label="MPL-903", senses=["physical"])})
    debate_placement(ont, resolve)
    n = ont.nodes["n1"]
    assert n.placement is PS.RESOLVED                  # not worsened
    assert n.metadata["mahalath"]["mpl_label"] == "MPL-903"
    assert "placement_source" not in n.metadata        # nothing changed


def test_debate_only_worsens_never_improves():
    # A contradiction stays a contradiction even if Mahalath finds the term grounded.
    ont = _ont([("n1", "the substrate is X", PS.CONTRADICTORY_PLACEMENT)])
    resolve = _resolver({"substrate": MahalathPlacement(
        term="substrate", mpl_label="MPL-902", senses=["structural"])})
    debate_placement(ont, resolve)
    assert ont.nodes["n1"].placement is PS.CONTRADICTORY_PLACEMENT


def test_unknown_term_unchanged():
    ont = _ont([("n1", "an unrelated claim", PS.RESOLVED)])
    informed = debate_placement(ont, _resolver({}))
    assert informed == 0
    assert ont.nodes["n1"].placement is PS.RESOLVED
    assert "mahalath" not in ont.nodes["n1"].metadata
