"""Executable provider API for Milcah specialist calls.

`milcah.contract` stays the pure schema/adapter layer. This module is the runtime
entrypoint: accept a `SpecialistRequest`, ingest/extract the framework text, run
Milcah orchestration, and adapt the rich result back to the flat public contract.
The seams are injectable so Tirzah and tests can exercise the provider path
without requiring a Hoglah daemon.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from typing import Any, Callable

from milcah.contract import (
    SpecialistRequest,
    SpecialistResult,
    specialist_result_from_orchestration,
    validate_specialist_request,
    validate_specialist_result,
)
from milcah.extraction import RuleBasedExtractor, extract
from milcah.ingestion import ingest_text
from milcah.models import Framework, ReasoningUnit, SourceType
from milcah.orchestration import OrchestrationConfig, orchestrate

ExtractUnitsFn = Callable[[Framework], list[ReasoningUnit]]
OrchestrateFn = Callable[[Framework, list[ReasoningUnit]], Any]
AdaptFn = Callable[[Any], SpecialistResult]


@dataclass
class SpecialistConfig:
    """Runtime options for a provider-side specialist call.

    ``extractor="hoglah"`` uses the LLM quality path for unit extraction
    (FR2) instead of the deterministic rule baseline. ``research`` supplies a
    WebResearchClient used only for mode="research" requests — without one,
    research mode runs the same pipeline as coherence (documented behaviour).
    """

    orchestration: OrchestrationConfig = field(default_factory=OrchestrationConfig)
    source_type: SourceType = SourceType.DOCUMENT
    extractor: str = "rule"  # "rule" | "hoglah"
    research: Any = None  # WebResearchClient for mode="research"


def coerce_specialist_request(request: Any) -> SpecialistRequest | None:
    """Convert a JSON-like request into `SpecialistRequest`, applying defaults.

    The public manifest requires only `query`; dataclass defaults supply the rest.
    Unknown fields are ignored so callers can pass transport-level metadata without
    breaking the provider.
    """
    if isinstance(request, SpecialistRequest):
        return request
    if not isinstance(request, dict):
        return None
    names = {f.name for f in fields(SpecialistRequest)}
    data = {k: v for k, v in request.items() if k in names}
    if "query" not in data:
        data["query"] = ""
    return SpecialistRequest(**data)


def run_specialist(
    request: Any,
    *,
    config: SpecialistConfig | None = None,
    extract_units: ExtractUnitsFn | None = None,
    orchestrator: OrchestrateFn | None = None,
    adapt: AdaptFn = specialist_result_from_orchestration,
) -> SpecialistResult:
    """Run Milcah as a bounded specialist and return the public contract result.

    Invalid requests and runtime failures return a conformant `SpecialistResult`
    with `terminal_reason="blocked"` rather than leaking engine exceptions across
    the specialist boundary.
    """
    cfg = config or SpecialistConfig()
    req = coerce_specialist_request(request)
    if req is None:
        return _blocked(["request must be an object"])

    errors = validate_specialist_request(req)
    if errors:
        return _blocked(errors, request=req)

    try:
        framework = _framework_from_request(req, source_type=cfg.source_type)
        if extract_units:
            units = extract_units(framework)
        elif cfg.extractor == "hoglah":
            from milcah.hoglah_extractor import HoglahExtractor
            from milcah.orchestration import Role

            units = extract(framework, HoglahExtractor(cfg.orchestration.hoglah_config(Role.PROPOSER)))
        else:
            units = extract(framework, RuleBasedExtractor())
        run_config = _bounded_config(cfg.orchestration, req)
        if req.mode == "research" and cfg.research is not None:
            run_config = replace(run_config, research=cfg.research)
        orchestration = (
            orchestrator(framework, units)
            if orchestrator
            else orchestrate(framework, units, config=run_config)
        )
    except Exception as exc:  # provider boundary: callers get a terminal reason
        return _blocked([type(exc).__name__], request=req)

    if orchestration is None:
        return SpecialistResult(
            terminal_reason="insufficient_evidence",
            trace_metadata=_trace_metadata(req),
        )

    try:
        result = adapt(orchestration)
    except Exception as exc:
        return _blocked([type(exc).__name__], request=req)

    try:
        result = _coerce_specialist_result(result)
    except Exception as exc:
        return _blocked([type(exc).__name__], request=req)
    result.trace_metadata = {**result.trace_metadata, **_trace_metadata(req)}

    result_errors = validate_specialist_result(result)
    if result_errors:
        return _blocked(result_errors, request=req)
    return result


def _framework_from_request(request: SpecialistRequest, *, source_type: SourceType) -> Framework:
    text = request.context or request.query
    return ingest_text(
        text,
        title=(request.query[:80] or "specialist request"),
        source_type=source_type,
        metadata={
            "specialist_query": request.query,
            "specialist_mode": request.mode,
            **({"trace_id": request.trace_id} if request.trace_id else {}),
            **({"session_id": request.session_id} if request.session_id else {}),
        },
    )


def _bounded_config(config: OrchestrationConfig, request: SpecialistRequest) -> OrchestrationConfig:
    try:
        requested_depth = max(0, int(request.max_iterations))
    except (TypeError, ValueError):
        requested_depth = config.max_depth
    return replace(config, max_depth=min(config.max_depth, requested_depth))


def _trace_metadata(request: SpecialistRequest) -> dict[str, Any]:
    return {
        "mode": request.mode,
        **({"trace_id": request.trace_id} if request.trace_id else {}),
        **({"session_id": request.session_id} if request.session_id else {}),
    }


def _coerce_specialist_result(result: Any) -> SpecialistResult:
    if isinstance(result, SpecialistResult):
        return result
    if hasattr(result, "to_dict"):
        data = result.to_dict()
    elif isinstance(result, dict):
        data = result
    elif hasattr(result, "__dict__"):
        names = {f.name for f in fields(SpecialistResult)}
        data = {k: v for k, v in vars(result).items() if k in names}
    else:
        data = result
    return SpecialistResult(**data)


def _blocked(errors: list[str], *, request: SpecialistRequest | None = None) -> SpecialistResult:
    trace_metadata: dict[str, Any] = {"validation_errors": errors}
    if request is not None:
        trace_metadata.update(_trace_metadata(request))
    return SpecialistResult(terminal_reason="blocked", trace_metadata=trace_metadata)
