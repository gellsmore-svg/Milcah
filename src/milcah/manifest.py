"""Milcah's Keturah manifest — its LLM-consumable interfaces.

Built from milcah.contract so the published interface and the enforced specialist
contract share one source. Exposed via build_manifest()/to_mcp().
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

from keturah import Manifest, capability, manifest

from milcah.contract import REQUEST_FIELDS, SPECIALIST_MODES, TERMINAL_REASONS


def _version() -> str:
    try:
        return _pkg_version("milcah")
    except PackageNotFoundError:
        return "0.0.0+source"


def _coherence_input_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "the claim/framework to pressure-test"},
            "mode": {
                "type": "string",
                "enum": sorted(SPECIALIST_MODES),
                "default": "coherence",
            },
            "context": {"type": "string", "description": "the framework text to analyse"},
            "max_iterations": {
                "type": "integer",
                "minimum": 0,
                "default": 3,
                "description": "upper bound on specialist recursion depth",
            },
            "trace_id": {"type": "string", "description": "caller trace identifier"},
            "session_id": {"type": "string", "description": "caller session identifier"},
        },
        "required": list(REQUEST_FIELDS),
    }


def _coherence_output_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "claims": {"type": "array", "items": {"type": "string"}},
            "objections": {"type": "array", "items": {"type": "string"}},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "citations": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "terminal_reason": {"type": "string", "enum": sorted(TERMINAL_REASONS)},
            "trace_metadata": {"type": "object"},
        },
        "required": [
            "claims",
            "objections",
            "evidence",
            "citations",
            "confidence",
            "terminal_reason",
            "trace_metadata",
        ],
    }


def _capability(name: str, description: str, **kwargs):
    """Build a capability; Stage-0 kwargs require keturah≥0.4 (fail-soft if older)."""
    try:
        return capability(name, description, **kwargs)
    except TypeError:
        # Pre-0.4 keturah: drop Stage-0 fields.
        for key in ("negotiable", "semantics", "evidence", "cost", "failure_modes"):
            kwargs.pop(key, None)
        return capability(name, description, **kwargs)


def build_manifest() -> Manifest:
    # `critique` is the Deborah ASSUMES / CALL name for the same specialist surface
    # as `coherence_check` (Tirzah planner + MCP). Both share schemas and tags.
    coherence_desc = (
        "Pressure-test a claim/framework for internal coherence, or run counter-framework "
        "research. Returns claims, objections, evidence, citations, a confidence in [0,1], "
        "and a terminal_reason."
    )
    stage0 = dict(
        negotiable=True,
        semantics={
            "purpose": coherence_desc,
            "can": ["detect-contradiction", "detect-unsupported-inference"],
            "cannot": ["establish-ground-truth", "retrieve-sources"],
        },
        evidence={"provides": ["objections", "counter-frameworks"], "confidence": "heuristic"},
        cost={"model_calls": "1..3", "budget_class": "medium"},
        failure_modes=["underspecified-claim", "domain-out-of-scope", "blocked"],
    )
    return manifest(
        "milcah",
        version=_version(),
        description="Specialist recursive-coherence and counter-framework research engine.",
        capabilities=[
            _capability(
                "coherence_check",
                coherence_desc,
                input_schema=_coherence_input_schema(),
                output_schema=_coherence_output_schema(),
                tags=["specialist", "coherence", "planner"],
                **stage0,
            ),
            _capability(
                "critique",
                coherence_desc
                + " Alias used by Deborah PLAN ASSUMES/CALL (milcah.critique).",
                input_schema=_coherence_input_schema(),
                output_schema=_coherence_output_schema(),
                tags=["specialist", "coherence", "critique", "evaluate", "planner"],
                **stage0,
            ),
            _capability(
                "validate_against_intent",
                "Score whether a provisional reading / critique aligns with declared "
                "intent and outcomes (intent_alignment criterion). May re-run critique "
                "when no prior evaluate artifact exists.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "intent": {"type": "string"},
                        "outcomes": {"type": "array", "items": {"type": "string"}},
                        "query": {"type": "string"},
                        "context": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "criteria": {"type": "array", "items": {"type": "string"}},
                        "scores": {"type": "object"},
                        "objections": {"type": "array", "items": {"type": "string"}},
                        "intent": {"type": "string"},
                    },
                },
                tags=["specialist", "evaluate", "intent", "planner"],
                **stage0,
            ),
            _capability(
                "assess_confidence",
                "Aggregate confidence bands from prior observe/infer/evaluate step "
                "artifacts; flag residual when inference is below a floor.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "confidence_floor": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        }
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "criteria": {"type": "array"},
                        "scores": {"type": "object"},
                        "confidence": {"type": "object"},
                    },
                },
                tags=["specialist", "evaluate", "confidence"],
                negotiable=False,
                evidence={"provides": ["confidence bands"], "confidence": "heuristic"},
                cost={"model_calls": "0", "budget_class": "free"},
                failure_modes=["missing_prior_artifacts"],
            ),
        ],
    )
