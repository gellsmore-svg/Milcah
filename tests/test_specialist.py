from types import SimpleNamespace

from milcah.contract import SpecialistRequest, validate_specialist_result
from milcah.models import ReasoningUnit, ReasoningUnitType as RT
from milcah.specialist import coerce_specialist_request, run_specialist


def _fake_orchestration(unit, *, coherence=0.66):
    return SimpleNamespace(
        reasoning=SimpleNamespace(units=[unit]),
        challenge=SimpleNamespace(
            objections=[SimpleNamespace(text="A fails when Y")],
            counter_frameworks=[SimpleNamespace(title="Rival R")],
        ),
        metrics=SimpleNamespace(global_coherence=coherence),
        roles={"proposer": "m_prop"},
        trace=[{"role": "proposer"}],
    )


def test_coerce_specialist_request_applies_dataclass_defaults():
    request = coerce_specialist_request({"query": "Is this coherent?"})
    assert request == SpecialistRequest(query="Is this coherent?")
    assert request.mode == "coherence"


def test_run_specialist_builds_framework_and_returns_contract_result():
    captured = {}

    def extract_units(framework):
        captured["raw_text"] = framework.raw_text
        captured["title"] = framework.title
        captured["metadata"] = framework.metadata
        return [
            ReasoningUnit.make(
                framework_id=framework.id,
                unit_type=RT.CLAIM,
                text="X holds under A",
            )
        ]

    def orchestrator(framework, units):
        captured["unit_framework_id"] = units[0].framework_id
        return _fake_orchestration(units[0])

    result = run_specialist(
        {
            "query": "Is the framework coherent?",
            "context": "X holds under A.",
            "trace_id": "trace_1",
            "session_id": "session_1",
        },
        extract_units=extract_units,
        orchestrator=orchestrator,
    )

    assert validate_specialist_result(result) == []
    assert captured["raw_text"] == "X holds under A."
    assert captured["title"] == "Is the framework coherent?"
    assert captured["metadata"]["specialist_query"] == "Is the framework coherent?"
    assert captured["unit_framework_id"]
    assert result.claims == ["X holds under A"]
    assert result.objections == ["A fails when Y"]
    assert result.evidence == ["Rival R"]
    assert result.confidence == 0.66
    assert result.trace_metadata["trace_id"] == "trace_1"
    assert result.trace_metadata["session_id"] == "session_1"
    assert result.trace_metadata["mode"] == "coherence"


def test_run_specialist_invalid_request_returns_conformant_blocked_result():
    result = run_specialist({"query": "", "mode": "nonsense"})
    assert validate_specialist_result(result) == []
    assert result.terminal_reason == "blocked"
    assert any("query must be non-empty" in e for e in result.trace_metadata["validation_errors"])
    assert any("invalid mode" in e for e in result.trace_metadata["validation_errors"])


def test_run_specialist_empty_orchestration_returns_insufficient_evidence():
    result = run_specialist(
        SpecialistRequest(query="q"),
        extract_units=lambda framework: [],
        orchestrator=lambda framework, units: None,
    )
    assert validate_specialist_result(result) == []
    assert result.terminal_reason == "insufficient_evidence"


def test_run_specialist_accepts_dict_like_adapter_results():
    result = run_specialist(
        SpecialistRequest(query="q"),
        extract_units=lambda framework: [],
        orchestrator=lambda framework, units: object(),
        adapt=lambda orchestration: SimpleNamespace(claims=["adapted claim"]),
    )
    assert validate_specialist_result(result) == []
    assert result.claims == ["adapted claim"]
    assert result.trace_metadata["mode"] == "coherence"


# --- correlation: cost must be attributable to the run that caused it -------


def test_session_and_trace_ids_reach_the_hoglah_job_metadata():
    """Without this the model calls land under the generic "hoglah" session and
    per-run cost cannot be measured — which is exactly what happened in
    Experiment 1A, where every run reported zero tokens."""
    from milcah.orchestration import OrchestrationConfig, Role
    from milcah.specialist import _bounded_config

    request = SpecialistRequest(
        query="q", session_id="exp1-run-3", trace_id="trace-abc", max_iterations=1
    )
    config = _bounded_config(OrchestrationConfig(), request)

    assert config.session_id == "exp1-run-3"
    assert config.trace_id == "trace-abc"

    # The *submitter* is what actually sends the job, so test it there — a
    # helper on the extractor alone left both transports raising AttributeError.
    from milcah.hoglah_extractor import _StoreSubmitter

    metadata = _StoreSubmitter(config.hoglah_config(Role.PROPOSER))._job_metadata()
    assert metadata["session_id"] == "exp1-run-3"
    assert metadata["trace_id"] == "trace-abc"
    assert metadata["source"] == "milcah"


def test_absent_correlation_ids_are_omitted_not_sent_as_none():
    """Hoglah falls back to the "hoglah" session on a missing key; a literal
    None would defeat that fallback."""
    from milcah.orchestration import OrchestrationConfig, Role

    from milcah.hoglah_extractor import _StoreSubmitter

    metadata = _StoreSubmitter(
        OrchestrationConfig().hoglah_config(Role.PROPOSER)
    )._job_metadata()
    assert metadata == {"source": "milcah"}
