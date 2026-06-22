import json

from milcah.fallacy import (
    FallacyType,
    analyse_fallacies,
    build_fallacy_prompt,
    number_steps,
    parse_fallacy_response,
)
from milcah.ingestion import ingest_text
from milcah.models import ReasoningUnit, ReasoningUnitType as RT


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
