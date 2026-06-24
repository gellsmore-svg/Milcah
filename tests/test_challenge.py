import json

from milcah.challenge import (
    build_challenge_prompt,
    challenge_framework,
    parse_challenge_response,
    select_claims,
)
from milcah.ingestion import ingest_text
from milcah.models import ReasoningUnit, ReasoningUnitType as RT


def _u(t, text):
    return ReasoningUnit.make(framework_id="f", unit_type=t, text=text)


def test_select_claims_filters_and_dedups():
    units = [_u(RT.OBSERVATION, "obs"), _u(RT.CLAIM, "c1"), _u(RT.CLAIM, "c1"), _u(RT.CONCLUSION, "con"), _u(RT.ENTHYMEME, "e")]
    claims = select_claims(units, limit=8)
    assert "c1" in claims and "con" in claims
    assert claims.count("c1") == 1  # deduped
    assert "obs" not in claims and "e" not in claims  # not challengeable types


def test_build_challenge_prompt_invokes_burden_symmetry():
    prompt = build_challenge_prompt("My Framework", ["claim A", "claim B"])
    assert "same scrutiny" in prompt.lower() and "no exemptions" in prompt.lower()
    assert "claim A" in prompt and "counter_frameworks" in prompt and "JSON object" in prompt


def test_parse_challenge_response_objections_and_counter_frameworks():
    raw = json.dumps(
        {
            "objections": [
                {"type": "claim", "text": "that ignores X", "targets": "claim A"},
                {"type": "not_a_type", "text": "dropped"},
            ],
            "counter_frameworks": [
                {"name": "Alt", "summary": "a different basis", "units": [{"type": "claim", "text": "alt claim"}]},
                {"name": "", "summary": "unnamed", "units": []},
            ],
        }
    )
    ch = parse_challenge_response(raw, "f")
    assert len(ch.objections) == 1
    assert ch.objections[0].metadata["role"] == "objection"
    assert ch.objections[0].metadata["targets"] == "claim A"
    assert len(ch.counter_frameworks) == 1  # the unnamed one is dropped
    cf = ch.counter_frameworks[0]
    assert cf.name == "Alt" and len(cf.units) == 1
    assert cf.units[0].metadata["role"] == "counter_framework"
    assert cf.units[0].metadata["framework_name"] == "Alt"


def test_parse_challenge_non_json():
    ch = parse_challenge_response("no json", "f")
    assert ch.objections == [] and ch.counter_frameworks == []


def test_challenge_framework_with_injected_generate():
    fw = ingest_text("Matter is topological form.", title="T")
    units = [_u(RT.CLAIM, "Matter is topological form.")]
    captured = {}

    def gen(prompt, model):
        captured["prompt"], captured["model"] = prompt, model
        return json.dumps({"objections": [{"type": "claim", "text": "obj", "targets": "c"}], "counter_frameworks": []})

    ch = challenge_framework(fw, units, generate=gen, model="m")
    assert len(ch.objections) == 1
    assert "Matter is topological form." in captured["prompt"] and captured["model"] == "m"


def test_challenge_research_is_in_prompt_and_unit_provenance():
    from milcah.web_research import ResearchSource
    fw = ingest_text("Matter is form.", title="Researchable")
    units = [_u(RT.CLAIM, "Matter is form.")]
    captured = {}
    class Research:
        def research(self, query):
            captured["query"] = query
            return [ResearchSource(title="Paper", url="https://example.test/p", snippet="counter evidence")]
    def gen(prompt, model):
        captured["prompt"] = prompt
        return json.dumps({"objections": [{"type": "claim", "text": "objection", "targets": "Matter is form."}], "counter_frameworks": []})
    result = challenge_framework(fw, units, generate=gen, model="m", research=Research())
    assert "Researchable" in captured["query"]
    assert "UNTRUSTED EXTERNAL EVIDENCE" in captured["prompt"]
    assert result.objections[0].metadata["research_sources"][0]["url"] == "https://example.test/p"
