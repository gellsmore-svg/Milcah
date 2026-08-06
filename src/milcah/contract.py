"""Public specialist-call contract (Tirzah <-> Milcah seam).

The provider-side mirror of Tirzah's ``tirzah.coherence`` contract: the request a
caller sends for a coherence/research specialist call, and the bounded, evidenced
result Milcah returns. Keeping this here (and tested against Milcah's own
``OrchestrationResult`` via :func:`specialist_result_from_orchestration`) means the
seam is guaranteed at the source — if Milcah's rich result shape changes, this
adapter and its test are the single place that has to stay honest.

Duck-typed so it imposes no runtime coupling on Milcah's internals; the
shapes themselves come from Keturah, which Milcah already depends on.
"""

from __future__ import annotations

from typing import Any

# The request/result shapes live in Keturah. They used to be written out here
# *and* in tirzah.coherence, and the two copies had already drifted — only the
# consumer side carried error/error_type, so a provider result could not
# represent its own failure. Re-exported so this module's callers are unaffected.
from keturah import (  # noqa: F401 — re-exported as this module's public API
    SPECIALIST_MODES,
    TERMINAL_REASONS,
    Evidence,
    SpecialistRequest,
    SpecialistResult,
    normalise_evidence,
)


REQUEST_FIELDS: tuple[str, ...] = ("query",)
RESULT_FIELDS: tuple[str, ...] = (
    "claims",
    "objections",
    "evidence",
    "citations",
    "confidence",
    "terminal_reason",
    "trace_metadata",
)


def validate_specialist_request(request: Any) -> list[str]:
    data = request.to_dict() if isinstance(request, SpecialistRequest) else request
    if not isinstance(data, dict):
        return ["request must be an object"]
    errors = [f"missing request field: {f}" for f in REQUEST_FIELDS if f not in data]
    if not data.get("query"):
        errors.append("query must be non-empty")
    mode = data.get("mode", "coherence")
    if mode not in SPECIALIST_MODES:
        errors.append(f"invalid mode: {mode!r} (allowed: {sorted(SPECIALIST_MODES)})")
    return errors


def validate_specialist_result(result: Any) -> list[str]:
    data = result.to_dict() if isinstance(result, SpecialistResult) else result
    if not isinstance(data, dict):
        return ["result must be an object"]
    errors = [f"missing result field: {f}" for f in RESULT_FIELDS if f not in data]
    for list_field in ("claims", "objections", "evidence", "citations"):
        if list_field in data and not isinstance(data[list_field], list):
            errors.append(f"{list_field} must be a list")
    confidence = data.get("confidence")
    if confidence is not None and not (isinstance(confidence, (int, float)) and 0.0 <= float(confidence) <= 1.0):
        errors.append("confidence must be a number in [0, 1]")
    reason = data.get("terminal_reason")
    if reason is not None and reason not in TERMINAL_REASONS:
        errors.append(f"invalid terminal_reason: {reason!r} (allowed: {sorted(TERMINAL_REASONS)})")
    return errors


def _text(unit: Any) -> str:
    return getattr(unit, "text", "") or ""


def _type_value(unit: Any) -> str:
    value = getattr(unit, "type", "")
    return str(getattr(value, "value", value))


def _research_citations(units: list[Any]) -> list[str]:
    citations: list[str] = []
    seen: set[str] = set()
    for unit in units:
        metadata = getattr(unit, "metadata", {}) or {}
        for source in metadata.get("research_sources") or []:
            url = source.get("url") if isinstance(source, dict) else getattr(source, "url", "")
            url = str(url or "").strip()
            if url and url not in seen:
                seen.add(url)
                citations.append(url)
    return citations


def specialist_result_from_orchestration(result: Any) -> SpecialistResult:
    """Adapt Milcah's rich ``OrchestrationResult`` to the flat public contract.

    Duck-typed (getattr) so it neither imports nor hard-couples to the internal
    dataclasses: claims from the reasoning units typed ``claim``; objections from the
    challenge; evidence from counter-framework titles; confidence from global
    coherence; provenance/trace summarised into trace_metadata.
    """
    reasoning = getattr(result, "reasoning", None)
    # ReasoningResult carries the expanded ONTOLOGY (recursive.py), not a flat
    # units list — claims are its claim-typed nodes. Fall back to result.ontology
    # (same object post-orchestration) and, for duck-typed test doubles, to a
    # legacy `units` attribute.
    ontology = getattr(reasoning, "ontology", None) or getattr(result, "ontology", None)
    nodes = list(getattr(ontology, "nodes", {}).values()) if ontology is not None else []
    if not nodes:
        nodes = list(getattr(reasoning, "units", []) or [])
    claims = [_text(n) for n in nodes if _type_value(n) == "claim" and _text(n)]

    challenge = getattr(result, "challenge", None)
    objection_units = list(getattr(challenge, "objections", []) or [])
    objections = [_text(o) for o in objection_units if _text(o)]
    counter = getattr(challenge, "counter_frameworks", []) or []
    evidence = [
        getattr(cf, "title", "") or getattr(cf, "name", "") or _text(cf) or str(cf) for cf in counter
    ]
    counter_units = [u for cf in counter for u in (getattr(cf, "units", []) or [])]

    metrics = getattr(result, "metrics", None)
    coherence = getattr(metrics, "global_coherence", 0.0) if metrics is not None else 0.0
    try:
        confidence = max(0.0, min(1.0, float(coherence)))
    except (TypeError, ValueError):
        confidence = 0.0

    trace = list(getattr(result, "trace", []) or [])
    return SpecialistResult(
        claims=claims,
        objections=objections,
        evidence=[e for e in evidence if e],
        citations=_research_citations([*objection_units, *counter_units]),
        confidence=confidence,
        terminal_reason=_terminal_reason_for(reasoning, claims, objections),
        trace_metadata={"trace_steps": len(trace), "roles": dict(getattr(result, "roles", {}) or {})},
    )


def _terminal_reason_for(reasoning: Any, claims: list[str], objections: list[str]) -> str:
    """Map the run's actual outcome onto the contract's TERMINAL_REASONS."""
    stop = str(getattr(reasoning, "stop_reason", "") or "")
    if stop in ("node_budget", "max_depth", "max_rounds"):
        return "max_iterations"
    if not claims:
        return "insufficient_evidence"
    if not objections:
        return "no_objections"
    return "converged"


CANONICAL_REQUEST: dict[str, Any] = {
    "query": "Is the proposed framework internally coherent?",
    "mode": "coherence",
    "context": "",
    "max_iterations": 3,
    "trace_id": "trace_abc",
    "session_id": "s1",
}

CANONICAL_RESULT: dict[str, Any] = {
    "claims": ["The framework is internally consistent under assumption A."],
    "objections": ["Assumption A is unsupported when condition X holds."],
    "evidence": ["Counterexample observed in dataset D."],
    "citations": ["https://example.org/source"],
    "confidence": 0.62,
    "terminal_reason": "converged",
    "trace_metadata": {"trace_id": "trace_abc", "iterations": 3},
}
