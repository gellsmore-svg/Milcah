"""Counter-framework research (FR5) — symmetric challenge.

The partner to the [recursive reasoner](recursive.py): for a framework, generate
the **strongest objections** to its claims and one or more **competing
frameworks** that could explain the same ground. This is where
[burden symmetry](../concepts/burden-symmetry.md) becomes operational — the prompt
applies the *same* scrutiny to every framework, with no exemptions.

The prompt build + response parse are pure and testable (the LLM seam);
`challenge_framework` applies an injectable `generate(prompt, model) -> output`;
`make_hoglah_challenger` runs it through Hoglah. (Web-retrieval-grounded
counter-research, per the architecture, is a later refinement.)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable

from milcah.hoglah_extractor import HoglahExtractorConfig, make_hoglah_submitter
from milcah.models import Framework, ReasoningUnit, ReasoningUnitType

_VALID_TYPES = {t.value for t in ReasoningUnitType}
# Claim-like unit types whose assertions are worth challenging.
_CHALLENGEABLE = {
    ReasoningUnitType.CLAIM,
    ReasoningUnitType.CONCLUSION,
    ReasoningUnitType.COMMITMENT,
    ReasoningUnitType.PRIMITIVE,
    ReasoningUnitType.ASSUMPTION,
}


@dataclass
class CounterFramework:
    name: str
    summary: str
    units: list[ReasoningUnit] = field(default_factory=list)


@dataclass
class Challenge:
    framework_id: str
    objections: list[ReasoningUnit] = field(default_factory=list)
    counter_frameworks: list[CounterFramework] = field(default_factory=list)


def select_claims(units: list[ReasoningUnit], *, limit: int = 8) -> list[str]:
    """The framework's challengeable assertions (claims/conclusions/…), de-duped."""
    seen: set[str] = set()
    claims: list[str] = []
    for u in units:
        if u.type in _CHALLENGEABLE and u.text not in seen:
            seen.add(u.text)
            claims.append(u.text)
        if len(claims) >= limit:
            break
    return claims


def build_challenge_prompt(framework_title: str, claims: list[str]) -> str:
    type_list = ", ".join(t.value for t in ReasoningUnitType)
    numbered = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(claims)) or "(no explicit claims)"
    return (
        "Challenge this framework. Apply the SAME scrutiny you would to any "
        "framework, with no exemptions.\n"
        f"Framework: {framework_title}\n"
        f"Its key claims:\n{numbered}\n\n"
        "Produce two things:\n"
        "1. objections — the strongest objections to these claims (each a typed "
        "reasoning unit; name the claim it targets).\n"
        "2. counter_frameworks — one or two alternative frameworks that could "
        "explain the same ground, each with a short name, a one-line summary, and "
        "its key claims as typed units.\n"
        f"Types (use exactly one per unit): {type_list}.\n\n"
        'Reply with ONLY a JSON object: {"objections": [{"type": ..., "text": ..., '
        '"targets": ...}], "counter_frameworks": [{"name": ..., "summary": ..., '
        '"units": [{"type": ..., "text": ...}]}]}. No prose.'
    )


def _extract_json_object(text: str):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _unit(framework_id: str, item: dict, *, role: str, **extra: Any) -> ReasoningUnit | None:
    raw_type = str(item.get("type", "")).strip().lower()
    text = str(item.get("text", "")).strip()
    if raw_type not in _VALID_TYPES or not text:
        return None
    return ReasoningUnit.make(
        framework_id=framework_id,
        unit_type=ReasoningUnitType(raw_type),
        text=text,
        markers=["challenge", role],
        metadata={"role": role, **extra},
    )


def parse_challenge_response(text: str, framework_id: str) -> Challenge:
    """Parse a challenge response into objections + counter-frameworks (hostile
    input: malformed entries dropped, unknown types skipped)."""
    challenge = Challenge(framework_id=framework_id)
    data = _extract_json_object(text)
    if not isinstance(data, dict):
        return challenge

    for item in data.get("objections") or []:
        if isinstance(item, dict):
            unit = _unit(framework_id, item, role="objection", targets=str(item.get("targets", "")).strip())
            if unit:
                challenge.objections.append(unit)

    for cf in data.get("counter_frameworks") or []:
        if not isinstance(cf, dict):
            continue
        name = str(cf.get("name", "")).strip()
        if not name:
            continue
        units = []
        for item in cf.get("units") or []:
            if isinstance(item, dict):
                unit = _unit(framework_id, item, role="counter_framework", framework_name=name)
                if unit:
                    units.append(unit)
        challenge.counter_frameworks.append(
            CounterFramework(name=name, summary=str(cf.get("summary", "")).strip(), units=units)
        )
    return challenge


GenerateFn = Callable[[str, str], str]


def challenge_framework(
    framework: Framework,
    units: list[ReasoningUnit],
    *,
    generate: GenerateFn,
    model: str,
    max_claims: int = 8,
) -> Challenge:
    prompt = build_challenge_prompt(framework.title, select_claims(units, limit=max_claims))
    return parse_challenge_response(generate(prompt, model), framework.id)


def make_hoglah_challenger(config: HoglahExtractorConfig) -> GenerateFn:
    submitter = make_hoglah_submitter(config)

    def generate(prompt: str, model: str) -> str:
        return submitter.run(prompt, model)

    return generate


def to_jsonable(value: Any) -> Any:
    if isinstance(value, (Challenge, CounterFramework, ReasoningUnit)):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    return value
