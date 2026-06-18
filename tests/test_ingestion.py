from milcah.ingestion import ingest_file, ingest_text, segment_text
from milcah.models import SourceType


def test_segment_text_splits_paragraphs_and_trims() -> None:
    text = "First para.\n\n  Second   para   here.\n\n\nThird."
    segments = segment_text(text)
    assert [s.text for s in segments] == ["First para.", "Second para here.", "Third."]
    assert [s.index for s in segments] == [0, 1, 2]


def test_ingest_text_derives_title_and_is_deterministic() -> None:
    text = "# Vorton Theory\n\nMatter is stable topology.\n\nIdentity is configuration."
    fw1 = ingest_text(text)
    fw2 = ingest_text(text)
    assert fw1.title == "Vorton Theory"
    assert fw1.source_type == SourceType.DOCUMENT
    # heading line + two body paragraphs = 3 segments (the title is derived from
    # the heading but the heading is still content).
    assert len(fw1.segments) == 3
    # deterministic id for identical input
    assert fw1.id == fw2.id


def test_ingest_text_explicit_title_and_metadata() -> None:
    fw = ingest_text("A claim.", title="My Framework", metadata={"k": "v"})
    assert fw.title == "My Framework"
    assert fw.metadata["k"] == "v"


def test_conversation_segments_by_turn() -> None:
    convo = "Alice: I think matter is topology.\ncontinued thought.\nBob: Why assume that?"
    fw = ingest_text(convo, source_type=SourceType.CONVERSATION)
    assert len(fw.segments) == 2
    assert fw.segments[0].text.startswith("Alice:")
    assert "continued thought" in fw.segments[0].text  # non-speaker line joined the turn
    assert fw.segments[1].text.startswith("Bob:")


def test_ingest_file_infers_type_and_title(tmp_path) -> None:
    p = tmp_path / "my-framework.txt"
    p.write_text("Observation: the sky is blue.", encoding="utf-8")
    fw = ingest_file(p)
    assert fw.title == "my framework"
    assert fw.source_type == SourceType.DOCUMENT
    assert fw.metadata["source_path"] == str(p)

    j = tmp_path / "ontology.json"
    j.write_text("{}", encoding="utf-8")
    assert ingest_file(j).source_type == SourceType.STRUCTURED_ONTOLOGY
