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


def build_manifest() -> Manifest:
    # `critique` is the Deborah ASSUMES / CALL name for the same specialist surface
    # as `coherence_check` (Tirzah planner + MCP). Both share schemas and tags.
    coherence_desc = (
        "Pressure-test a claim/framework for internal coherence, or run counter-framework "
        "research. Returns claims, objections, evidence, citations, a confidence in [0,1], "
        "and a terminal_reason."
    )
    return manifest(
        "milcah",
        version=_version(),
        description="Specialist recursive-coherence and counter-framework research engine.",
        capabilities=[
            capability(
                "coherence_check",
                coherence_desc,
                input_schema=_coherence_input_schema(),
                output_schema=_coherence_output_schema(),
                tags=["specialist", "coherence", "planner"],
            ),
            capability(
                "critique",
                coherence_desc
                + " Alias used by Deborah PLAN ASSUMES/CALL (milcah.critique).",
                input_schema=_coherence_input_schema(),
                output_schema=_coherence_output_schema(),
                tags=["specialist", "coherence", "critique", "evaluate", "planner"],
            ),
        ],
    )
