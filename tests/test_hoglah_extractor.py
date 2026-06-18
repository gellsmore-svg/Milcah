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
