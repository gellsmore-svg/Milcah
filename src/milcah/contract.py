"""Public specialist-call contract (Tirzah <-> Milcah seam).

The provider-side mirror of Tirzah's ``tirzah.coherence`` contract: the request a
caller sends for a coherence/research specialist call, and the bounded, evidenced
result Milcah returns. Keeping this here (and tested against Milcah's own
``OrchestrationResult`` via :func:`specialist_result_from_orchestration`) means the
seam is guaranteed at the source — if Milcah's rich result shape changes, this
adapter and its test are the single place that has to stay honest.

Pure-stdlib + duck-typed so it imposes no import cost and no coupling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SPECIALIST_MODES = frozenset({"coherence", "research"})
TERMINAL_REASONS = frozenset(
    {"converged", "max_iterations", "no_objections", "insufficient_evidence", "blocked"}
)


@dataclass
class SpecialistRequest:
    query: str
    mode: str = "coherence"
    context: str = ""
    max_iterations: int = 3
    trace_id: str | None = None
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SpecialistResult:
    claims: list[str] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    terminal_reason: str = "converged"
    trace_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


REQUEST_FIELDS: tuple[str, ...] = ("query", "mode")
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
    if data.get("mode") not in SPECIALIST_MODES:
        errors.append(f"invalid mode: {data.get('mode')!r} (allowed: {sorted(SPECIALIST_MODES)})")
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


def specialist_result_from_orchestration(result: Any) -> SpecialistResult:
    """Adapt Milcah's rich ``OrchestrationResult`` to the flat public contract.

    Duck-typed (getattr) so it neither imports nor hard-couples to the internal
    dataclasses: claims from the reasoning units typed ``claim``; objections from the
    challenge; evidence from counter-framework titles; confidence from global
    coherence; provenance/trace summarised into trace_metadata.
    """
    reasoning = getattr(result, "reasoning", None)
    units = list(getattr(reasoning, "units", []) or [])
    claims = [_text(u) for u in units if str(getattr(u, "type", "")) == "claim" and _text(u)]

    challenge = getattr(result, "challenge", None)
    objections = [_text(o) for o in getattr(challenge, "objections", []) or [] if _text(o)]
    counter = getattr(challenge, "counter_frameworks", []) or []
    evidence = [
        getattr(cf, "title", "") or getattr(cf, "name", "") or _text(cf) or str(cf) for cf in counter
    ]

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
        citations=[],
        confidence=confidence,
        terminal_reason="converged",
        trace_metadata={"trace_steps": len(trace), "roles": dict(getattr(result, "roles", {}) or {})},
    )


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
