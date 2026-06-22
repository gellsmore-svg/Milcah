import json

from milcah.fallacy import (
    FallacyFinding,
    FallacyType,
    analyse_fallacies,
    build_fallacy_prompt,
    mark_fallacies,
    number_steps,
    parse_fallacy_response,
)
from milcah.ingestion import ingest_text
from milcah.metrics import compute_metrics
from milcah.models import ReasoningUnit, ReasoningUnitType as RT
from milcah.ontology import PlacementState as PS, build_ontology


def _u(t, text, depends_on=None):
    return ReasoningUnit.make(framework_id="f", unit_type=t, text=text, metadata=None)


def test_number_steps_limit_and_order():
    units = [_u(RT.CLAIM, f"c{i}") for i in range(5)]
    steps = number_steps(units, limit=3)
    assert [s.text for s in steps] == ["c0", "c1", "c2"]


def test_build_prompt_makes_logical_form_dominant():
    steps = [_u(RT.CLAIM, "everyone agrees it is so")]
    prompt = build_fallacy_prompt("My Framework", steps)
    # the rhetorical-logic-cluster directive: judge form, not topical truth/popularity
    low = prompt.lower()
    assert "form of the inference" in low
    assert "popular" in low and "authority are not validity" in low
    assert "same logical scrutiny" in low
    # every FR6 fallacy name is offered
    for f in FallacyType:
        assert f.value in prompt
    assert "everyone agrees it is so" in prompt and "JSON object" in prompt


def test_build_prompt_shows_inferential_support():
    base = _u(RT.PRIMITIVE, "space is discrete")
    derived = ReasoningUnit.make(
        framework_id="f", unit_type=RT.CONCLUSION, text="therefore time is discrete",
    )
    derived.depends_on = [base.id]
    prompt = build_fallacy_prompt("T", [base, derived])
    assert "from: space is discrete" in prompt  # the step's support is shown


def test_parse_locates_findings_and_drops_bad_ones():
    steps = [_u(RT.CLAIM, "step one"), _u(RT.CLAIM, "step two")]
    raw = json.dumps(
        {
            "findings": [
                {"fallacy": "circularity", "step": 1, "explanation": "assumes its own conclusion"},
                {"fallacy": "not_a_fallacy", "step": 2, "explanation": "dropped"},
                {"fallacy": "contradiction", "step": 2, "explanation": ""},  # no explanation -> dropped
                {"fallacy": "appeal_to_popularity", "step": 99, "explanation": "out of range step"},
            ]
        }
    )
    report = parse_fallacy_response(raw, "f", steps)
    assert len(report.findings) == 2
    first = report.findings[0]
    assert first.fallacy is FallacyType.CIRCULARITY
    assert first.step_index == 1
    assert first.location_text == "step one"
    assert first.location_unit_id == steps[0].id
    # out-of-range step keeps the finding but leaves the location blank
    last = report.findings[1]
    assert last.fallacy is FallacyType.APPEAL_TO_POPULARITY
    assert last.location_text == "" and last.location_unit_id is None


def test_parse_non_json():
    report = parse_fallacy_response("no json here", "f", [])
    assert report.findings == []


def test_analyse_fallacies_with_injected_generate():
    fw = ingest_text("Everyone knows matter is topological form.", title="T")
    units = [_u(RT.CLAIM, "Everyone knows matter is topological form.")]
    captured = {}

    def gen(prompt, model):
        captured["prompt"], captured["model"] = prompt, model
        return json.dumps(
            {"findings": [{"fallacy": "appeal_to_popularity", "step": 1, "explanation": "wide belief is not support"}]}
        )

    report = analyse_fallacies(fw, units, generate=gen, model="m")
    assert len(report.findings) == 1
    assert report.findings[0].fallacy is FallacyType.APPEAL_TO_POPULARITY
    assert report.framework_id == fw.id
    assert captured["model"] == "m"
    assert "Everyone knows matter is topological form." in captured["prompt"]


def test_mark_fallacies_annotates_and_fractures():
    foundation = ReasoningUnit.make(framework_id="f", unit_type=RT.PRIMITIVE, text="a primitive")
    claim = ReasoningUnit.make(framework_id="f", unit_type=RT.CLAIM, text="a claim")
    ont = build_ontology("f", [foundation, claim])
    assert ont.nodes[claim.id].placement is PS.RESOLVED  # structural scaffold: resolved

    findings = [
        FallacyFinding(fallacy=FallacyType.CONTRADICTION, explanation="cannot both hold",
                       location_text="a claim", location_unit_id=claim.id, step_index=2),
        FallacyFinding(fallacy=FallacyType.APPEAL_TO_AUTHORITY, explanation="say-so is not support",
                       location_text="a primitive", location_unit_id=foundation.id, step_index=1),
        FallacyFinding(fallacy=FallacyType.EQUIVOCATION, explanation="no location",
                       location_text="", location_unit_id=None),
    ]
    marked = mark_fallacies(ont, findings)
    assert marked == 2  # the unlocated finding is skipped

    # contradiction elevates the node to a fracture (reasoned, not structural)
    assert ont.nodes[claim.id].placement is PS.CONTRADICTORY_PLACEMENT
    assert ont.nodes[claim.id].metadata["placement_source"] == "fallacy"
    # appeal-to-authority is recorded but does not re-place the node
    assert ont.nodes[foundation.id].placement is PS.RESOLVED
    assert ont.nodes[foundation.id].metadata["fallacies"][0]["fallacy"] == "appeal_to_authority"


def test_marked_fallacies_feed_the_metrics():
    claim = ReasoningUnit.make(framework_id="f", unit_type=RT.PRIMITIVE, text="a claim")
    ont = build_ontology("f", [claim])
    before = compute_metrics(ont)
    assert before.fallacy_load == 0 and before.fracture_density == 0.0

    mark_fallacies(ont, [FallacyFinding(
        fallacy=FallacyType.CIRCULARITY, explanation="assumes its own conclusion",
        location_text="a claim", location_unit_id=claim.id, step_index=1)])
    after = compute_metrics(ont)
    assert after.fallacy_load == 1
    assert after.fracture_density == 1.0  # circularity made the sole node a fracture
