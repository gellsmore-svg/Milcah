from types import SimpleNamespace

from milcah.contract import (
    CANONICAL_REQUEST,
    CANONICAL_RESULT,
    SpecialistRequest,
    SpecialistResult,
    specialist_result_from_orchestration,
    validate_specialist_request,
    validate_specialist_result,
)


def test_canonical_fixtures_conform():
    assert validate_specialist_request(CANONICAL_REQUEST) == []
    assert validate_specialist_result(CANONICAL_RESULT) == []


def test_validation_catches_drift():
    errors = validate_specialist_result(
        {
            "claims": "nope",
            "objections": [],
            "evidence": [],
            "citations": [],
            "confidence": 2.0,
            "terminal_reason": "boom",
            "trace_metadata": {},
        }
    )
    assert any("claims must be a list" in e for e in errors)
    assert any("confidence must be a number in [0, 1]" in e for e in errors)
    assert any("invalid terminal_reason: 'boom'" in e for e in errors)
    assert any("invalid mode" in e for e in validate_specialist_request({"query": "q", "mode": "x"}))


def test_adapter_maps_orchestration_result_to_contract():
    # A duck-typed stand-in for milcah.orchestration.OrchestrationResult.
    fake = SimpleNamespace(
        reasoning=SimpleNamespace(
            units=[
                SimpleNamespace(type="claim", text="X holds under A"),
                SimpleNamespace(type="assumption", text="A is granted"),
            ]
        ),
        challenge=SimpleNamespace(
            objections=[SimpleNamespace(text="A fails when Y")],
            counter_frameworks=[SimpleNamespace(title="Rival framework R")],
        ),
        metrics=SimpleNamespace(global_coherence=0.72),
        roles={"proposer": "gemma"},
        trace=[{"step": "expand"}, {"step": "challenge"}],
    )
    result = specialist_result_from_orchestration(fake)
    assert validate_specialist_result(result) == []  # adapter output is conformant
    assert result.claims == ["X holds under A"]  # only 'claim'-typed units
    assert result.objections == ["A fails when Y"]
    assert result.evidence == ["Rival framework R"]
    assert result.confidence == 0.72
    assert result.trace_metadata["trace_steps"] == 2


def test_adapter_is_robust_to_a_minimal_result():
    result = specialist_result_from_orchestration(SimpleNamespace())
    assert validate_specialist_result(result) == []  # empty-but-conformant
    assert result.confidence == 0.0


def test_request_dataclass_roundtrips():
    assert validate_specialist_request(SpecialistRequest(query="q", mode="research")) == []
    assert validate_specialist_result(SpecialistResult(claims=["c"], confidence=0.4)) == []
