"""Deborah estate adapter — milcah.critique as evaluate product."""

from types import SimpleNamespace

from milcah.deborah import (
    capability_index_entries,
    confidence_band,
    deborah_dispatch,
    make_critique_handler,
    specialist_to_evaluate,
)
from milcah.manifest import build_manifest


def test_confidence_bands():
    assert confidence_band(0.9) == "high"
    assert confidence_band(0.5) == "medium"
    assert confidence_band(0.2) == "low"
    assert confidence_band(0.0) == "unassessed"
    assert confidence_band("x") == "unassessed"


def test_specialist_to_evaluate_shape():
    result = SimpleNamespace(
        claims=["C holds"],
        objections=["C fails when X"],
        evidence=["Rival R"],
        citations=["https://example.test"],
        confidence=0.55,
        terminal_reason="converged",
        trace_metadata={},
    )
    product = specialist_to_evaluate(result)
    assert product["objections"] == ["C fails when X"]
    assert product["scores"]["internal_consistency"] == "medium"
    assert product["confidence"]["inference"] == "medium"
    assert "criteria" in product
    assert product["ranking"][0] == "open"  # objections → prefer open first


def test_critique_handler_with_injected_runner():
    def fake_run(request, config=None):
        return SimpleNamespace(
            claims=["ok"],
            objections=[],
            evidence=["e1"],
            citations=[],
            confidence=0.8,
            terminal_reason="no_objections",
            trace_metadata={},
        )

    handler = make_critique_handler(run_fn=fake_run)
    out = handler(
        {"construct": "CALL", "action": "milcah.critique — pressure-test"},
        {"claim": "Is space discrete?", "request": "Is space discrete?"},
    )
    assert out["status"] == "completed"
    assert out["result"]["claims"] == ["ok"]
    assert out["result"]["confidence"]["inference"] == "high"


def test_critique_handler_blocks_on_specialist_blocked():
    def blocked(request, config=None):
        return SimpleNamespace(
            claims=[],
            objections=[],
            evidence=[],
            citations=[],
            confidence=0.0,
            terminal_reason="blocked",
            trace_metadata={"validation_errors": ["query must be non-empty"]},
        )

    out = make_critique_handler(run_fn=blocked)({}, {"claim": ""})
    assert out["status"] == "blocked"
    assert out.get("residual") is True


def test_deborah_dispatch_keys():
    d = deborah_dispatch(run_fn=lambda *a, **k: SimpleNamespace(
        claims=[], objections=[], evidence=[], citations=[],
        confidence=0.0, terminal_reason="insufficient_evidence", trace_metadata={},
    ))
    assert "milcah.critique" in d
    assert "critique" in d
    assert "coherence_check" in d


def test_capability_index_entries_and_manifest_critique_alias():
    entries = capability_index_entries()
    assert "milcah.critique" in entries
    names = {c.name for c in build_manifest().capabilities}
    assert "coherence_check" in names
    assert "critique" in names


def test_default_critique_handler_with_injected_orchestrator_path():
    """Offline: inject run_specialist via make_critique_handler — no Hoglah."""
    from milcah.specialist import run_specialist
    from milcah.models import ReasoningUnit, ReasoningUnitType as RT
    from types import SimpleNamespace

    def extract_units(framework):
        return [
            ReasoningUnit.make(
                framework_id=framework.id,
                unit_type=RT.CLAIM,
                text="Space is discrete under A",
            )
        ]

    def orchestrator(framework, units):
        return SimpleNamespace(
            reasoning=SimpleNamespace(units=units),
            challenge=SimpleNamespace(
                objections=[SimpleNamespace(text="A is unsupported")],
                counter_frameworks=[],
            ),
            metrics=SimpleNamespace(global_coherence=0.4),
            roles={"proposer": "rule"},
            trace=[{"role": "proposer"}],
        )

    def run_fn(request, config=None):
        return run_specialist(
            request, config=config, extract_units=extract_units, orchestrator=orchestrator
        )

    out = make_critique_handler(run_fn=run_fn)(
        {"construct": "CALL", "action": "milcah.critique"},
        {
            "claim": "Is the framework coherent?",
            "artifacts": {
                "s2": {
                    "claim_restatement": "Space is discrete under assumption A.",
                }
            },
        },
    )
    assert out["status"] == "completed"
    assert "criteria" in out["result"]
    assert out["result"]["objections"]
