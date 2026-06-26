"""Milcah's Keturah manifest — its LLM-consumable interfaces.

Built from milcah.contract so the published interface and the enforced specialist
contract share one source. Exposed via build_manifest()/to_mcp().
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

from keturah import Manifest, capability, manifest

from milcah.contract import RESULT_FIELDS, SPECIALIST_MODES


def _version() -> str:
    try:
        return _pkg_version("milcah")
    except PackageNotFoundError:
        return "0.0.0+source"


def build_manifest() -> Manifest:
    return manifest(
        "milcah",
        version=_version(),
        description="Specialist recursive-coherence and counter-framework research engine.",
        capabilities=[
            capability(
                "coherence_check",
                "Pressure-test a claim/framework for internal coherence, or run counter-framework "
                "research. Returns claims, objections, evidence, citations, a confidence in [0,1], "
                "and a terminal_reason.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "the claim/framework to pressure-test"},
                        "mode": {"type": "string", "enum": sorted(SPECIALIST_MODES)},
                        "context": {"type": "string", "description": "the framework text to analyse"},
                    },
                    "required": ["query"],
                },
                output_schema={"type": "object", "properties": {field: {} for field in RESULT_FIELDS}},
                tags=["specialist", "coherence", "planner"],
            ),
        ],
    )
