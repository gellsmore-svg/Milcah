from milcah.extraction import (
    RuleBasedExtractor,
    build_extraction_prompt,
    classify_sentence,
    extract,
    parse_extraction_response,
    split_sentences,
)
from milcah.ingestion import ingest_text
from milcah.models import ReasoningUnitType


def test_classify_sentence_by_markers() -> None:
    assert classify_sentence("We assume space is continuous.")[0] == ReasoningUnitType.ASSUMPTION
    assert classify_sentence("Therefore identity is stable.")[0] == ReasoningUnitType.BRIDGE
    assert classify_sentence("We observe that the value drifts.")[0] == ReasoningUnitType.OBSERVATION
    assert classify_sentence("This must hold for the model.")[0] == ReasoningUnitType.COMMITMENT
    assert classify_sentence("In conclusion, the framework coheres.")[0] == ReasoningUnitType.CONCLUSION
    assert classify_sentence("By definition a vorton is a knot.")[0] == ReasoningUnitType.PRIMITIVE
    assert classify_sentence("Obviously the rest follows.")[0] == ReasoningUnitType.ENTHYMEME
    # a plain assertion with no markers is a claim
    unit_type, markers = classify_sentence("Matter is stable topology.")
    assert unit_type == ReasoningUnitType.CLAIM
    assert markers == []


def test_split_sentences() -> None:
    assert split_sentences("One. Two! Three?") == ["One.", "Two!", "Three?"]


def test_split_sentences_keeps_abbreviations() -> None:
    s = split_sentences("Dr. Smith disagrees. He cites Fig. 3 and p. 12.")
    assert len(s) == 2
    assert s[0].startswith("Dr.")
    s2 = split_sentences("Use e.g. remote work. It works.")
    assert len(s2) == 2


def test_classify_negation_and_collision() -> None:
    # Negation window: not a commitment / not an axiom / never assume
    assert classify_sentence("This does not necessarily follow from the premise.")[0] == ReasoningUnitType.CLAIM
    assert classify_sentence("That is not an axiom, it is a conjecture.")[0] == ReasoningUnitType.CLAIM
    assert classify_sentence("I never assume the reader knows this.")[0] == ReasoningUnitType.CLAIM
    # Earliest marker wins: "assume" before "measured"
    t, markers = classify_sentence(
        "We assume that measured output captures what matters about work."
    )
    assert t == ReasoningUnitType.ASSUMPTION
    assert "assume" in markers
    # Incidental everyday use should not over-type
    assert classify_sentence("The label is clearly printed on the box.")[0] == ReasoningUnitType.CLAIM
    assert classify_sentence("She left because it was raining.")[0] == ReasoningUnitType.CLAIM


def test_rule_based_extract_types_units_and_links_dependencies() -> None:
    text = (
        "We assume space is continuous. Matter is stable topology. "
        "Therefore identity is preserved."
    )
    fw = ingest_text(text, title="t")
    units = extract(fw)
    assert [u.type for u in units] == [
        ReasoningUnitType.ASSUMPTION,
        ReasoningUnitType.CLAIM,
        ReasoningUnitType.BRIDGE,
    ]
    # the bridge depends on the immediately preceding unit (the claim)
    bridge = units[-1]
    assert bridge.depends_on == [units[1].id]
    # markers are recorded as provenance
    assert "therefore" in bridge.markers
    # ids are stable across runs
    assert [u.id for u in extract(fw)] == [u.id for u in units]


def test_extract_default_is_rule_based() -> None:
    fw = ingest_text("A claim.", title="t")
    assert extract(fw) == RuleBasedExtractor().extract(fw)


def test_build_extraction_prompt_lists_types() -> None:
    fw = ingest_text("Matter is topology.", title="Vorton")
    prompt = build_extraction_prompt(fw)
    assert "observation" in prompt and "enthymeme" in prompt
    assert "Vorton" in prompt
    assert "JSON array" in prompt


def test_parse_extraction_response_filters_garbage() -> None:
    fw = ingest_text("x", title="t")
    raw = (
        'noise before ['
        '{"type": "claim", "text": "Matter is topology."},'
        '{"type": "bogus", "text": "dropped"},'
        '{"type": "assumption", "text": ""},'
        '{"type": "observation", "text": "We measured drift."}'
        '] noise after'
    )
    units = parse_extraction_response(raw, fw)
    assert [u.type for u in units] == [ReasoningUnitType.CLAIM, ReasoningUnitType.OBSERVATION]
    assert all(u.framework_id == fw.id and u.markers == ["llm"] for u in units)


def test_parse_extraction_response_handles_non_json() -> None:
    fw = ingest_text("x", title="t")
    assert parse_extraction_response("not json at all", fw) == []


def test_build_extraction_prompt_segment_excerpt() -> None:
    fw = ingest_text("the whole framework body", title="T")
    p = build_extraction_prompt(fw, text="just this excerpt")
    assert "just this excerpt" in p
    assert "EXCERPT" in p
    assert "the whole framework body" not in p  # only the excerpt, not the full text


def test_parse_extraction_response_tags_segment_index() -> None:
    fw = ingest_text("x", title="t")
    units = parse_extraction_response('[{"type":"claim","text":"a"}]', fw, segment_index=3)
    assert units[0].segment_index == 3
