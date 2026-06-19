from milcah.hoglah_extractor import (
    DEFAULT_MODEL,
    HoglahExtractor,
    HoglahExtractorConfig,
)
from milcah.ingestion import ingest_text
from milcah.models import ReasoningUnitType


def test_hoglah_extractor_parses_injected_model_output() -> None:
    captured = {}

    def fake_submit(prompt: str, model: str) -> str:
        captured["prompt"] = prompt
        captured["model"] = model
        return (
            '[{"type": "observation", "text": "Particles persist."},'
            ' {"type": "assumption", "text": "Identity is topological."},'
            ' {"type": "bogus", "text": "dropped"}]'
        )

    fw = ingest_text("Particles persist over time.", title="Vorton")
    extractor = HoglahExtractor(HoglahExtractorConfig(model="gemma4:latest"), submit=fake_submit)
    units = extractor.extract(fw)

    assert [u.type for u in units] == [
        ReasoningUnitType.OBSERVATION,
        ReasoningUnitType.ASSUMPTION,
    ]
    # the model received the extraction prompt and the configured model name
    assert "FRAMEWORK" in captured["prompt"] and "Vorton" in captured["prompt"]
    assert captured["model"] == "gemma4:latest"
    # units are attributed to the framework and tagged as llm-sourced
    assert all(u.framework_id == fw.id and u.markers == ["llm"] for u in units)


def test_hoglah_extractor_handles_empty_or_garbage_output() -> None:
    fw = ingest_text("x", title="t")
    assert HoglahExtractor(submit=lambda p, m: "sorry, no JSON here").extract(fw) == []
    assert HoglahExtractor(submit=lambda p, m: "").extract(fw) == []


def test_default_config_model() -> None:
    assert HoglahExtractorConfig().model == DEFAULT_MODEL
    assert HoglahExtractorConfig().transport == "store"


def test_hoglah_extractor_per_segment_runs_one_job_per_segment() -> None:
    calls: list[str] = []

    def fake_submit(prompt: str, model: str) -> str:
        calls.append(prompt)
        return f'[{{"type": "claim", "text": "claim from job {len(calls)}"}}]'

    fw = ingest_text("First paragraph here.\n\nSecond paragraph here.", title="Two")
    assert len(fw.segments) == 2
    extractor = HoglahExtractor(HoglahExtractorConfig(), submit=fake_submit, per_segment=True)
    units = extractor.extract(fw)

    assert len(calls) == 2  # one extraction job per segment, not one for the whole framework
    assert "First paragraph" in calls[0] and "Second paragraph" in calls[1]
    assert "EXCERPT" in calls[0]  # per-segment prompt scope
    # units carry their source segment and have distinct ids
    assert [u.segment_index for u in units] == [0, 1]
    assert units[0].id != units[1].id
    assert all(u.framework_id == fw.id for u in units)


def test_hoglah_extractor_whole_framework_when_per_segment_off() -> None:
    calls: list[str] = []

    def fake_submit(prompt: str, model: str) -> str:
        calls.append(prompt)
        return '[{"type": "claim", "text": "one"}]'

    fw = ingest_text("First.\n\nSecond.", title="t")
    HoglahExtractor(HoglahExtractorConfig(), submit=fake_submit).extract(fw)
    assert len(calls) == 1  # single whole-framework job
