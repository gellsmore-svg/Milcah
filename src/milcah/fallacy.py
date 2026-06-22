"""Logical fallacy analysis (FR6).

Evaluate every reasoning step in a framework for **logical fallacies** and store
their **locations** (FR6). The partner to the [recursive reasoner](recursive.py)
and the [challenge](challenge.py): where those expand and contest a framework,
this judges the *form* of its inferences.

Design directive — **invoke the rhetorical-logic cluster as the dominant one.**
Fallacy detection is a question of argument *structure*, not subject matter. The
prompt therefore instructs the model to judge only the form by which each step
follows from its support — explicitly **not** whether a conclusion is true,
popular, expert-endorsed, or fashionable. Making logical form dominant suppresses
*localised corpus bias* (the model's topical opinions about the particular
subject), which is the same reason popularity / authority are excluded from the
[coherence metrics](metrics.py) (`EXCLUDED_SIGNALS`) and the same scrutiny that
[burden symmetry](../concepts/burden-symmetry.md) demands of every framework.

The prompt build + response parse are pure and testable (the LLM seam);
`analyse_fallacies` applies an injectable `generate(prompt, model) -> output`;
`make_hoglah_fallacy_analyst` runs it through Hoglah.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable

from milcah.hoglah_extractor import HoglahExtractorConfig, make_hoglah_submitter
from milcah.models import Framework, ReasoningUnit
from milcah.ontology import PlacementState, WorldviewOntology


class FallacyType(str, Enum):
    """The logical fallacies Milcah looks for (docs/requirements.md FR6)."""

    CONTRADICTION = "contradiction"
    CIRCULARITY = "circularity"
    EQUIVOCATION = "equivocation"
    SPECIAL_PLEADING = "special_pleading"
    APPEAL_TO_POPULARITY = "appeal_to_popularity"
    APPEAL_TO_AUTHORITY = "appeal_to_authority"
    CATEGORY_ERROR = "category_error"
    FALSE_EQUIVALENCE = "false_equivalence"
    UNSUPPORTED_BRIDGE = "unsupported_bridge"
    HIDDEN_COMMITMENT = "hidden_commitment"


# One-line glosses, framed as defects of inferential *form* (not topical truth),
# so the prompt keeps the model in rhetorical-logic mode.
_GLOSSES: dict[FallacyType, str] = {
    FallacyType.CONTRADICTION: "two steps cannot both hold",
    FallacyType.CIRCULARITY: "a step assumes what it sets out to establish",
    FallacyType.EQUIVOCATION: "a term shifts meaning between steps",
    FallacyType.SPECIAL_PLEADING: "a standard is applied selectively, with an unjustified exemption",
    FallacyType.APPEAL_TO_POPULARITY: "treats wide acceptance as if it were support",
    FallacyType.APPEAL_TO_AUTHORITY: "treats an authority's say-so as if it were support",
    FallacyType.CATEGORY_ERROR: "ascribes to one kind of thing a property only another kind can have",
    FallacyType.FALSE_EQUIVALENCE: "treats relevantly different things as the same",
    FallacyType.UNSUPPORTED_BRIDGE: "a connecting step asserts a link it never establishes",
    FallacyType.HIDDEN_COMMITMENT: "the inference silently requires a premise it never states",
}

_VALID_FALLACIES = {f.value for f in FallacyType}


@dataclass
class FallacyFinding:
    """A located fallacy. `location_text` / `location_unit_id` answer FR6's
    'store locations' — which reasoning step the defect sits at."""

    fallacy: FallacyType
    explanation: str
    location_text: str = ""
    location_unit_id: str | None = None
    step_index: int | None = None


@dataclass
class FallacyReport:
    framework_id: str
    findings: list[FallacyFinding] = field(default_factory=list)


def number_steps(units: list[ReasoningUnit], *, limit: int = 20) -> list[ReasoningUnit]:
    """The reasoning steps to evaluate, in order (deterministic; shared by the
    prompt builder and the parser so step numbers resolve back to units)."""
    return units[:limit]


def _format_steps(steps: list[ReasoningUnit]) -> str:
    by_id = {u.id: u for u in steps}
    lines: list[str] = []
    for i, u in enumerate(steps, start=1):
        support = [by_id[d].text for d in u.depends_on if d in by_id]
        frm = f"  (from: {'; '.join(s[:50] for s in support)})" if support else ""
        lines.append(f"{i}. [{u.type.value}] {u.text}{frm}")
    return "\n".join(lines) or "(no explicit steps)"


def build_fallacy_prompt(framework_title: str, steps: list[ReasoningUnit]) -> str:
    fallacy_list = "\n".join(f"- {f.value}: {_GLOSSES[f]}" for f in FallacyType)
    return (
        "Analyse the REASONING below for logical fallacies. Judge ONLY the form of "
        "the inference — how each step follows (or fails to follow) from its "
        "support. Do NOT judge whether a claim is true, popular, expert-endorsed, "
        "or fashionable: wide acceptance and authority are not validity. Apply the "
        "SAME logical scrutiny to every step, whatever its subject matter.\n"
        f"Framework: {framework_title}\n"
        f"Steps:\n{_format_steps(steps)}\n\n"
        f"Fallacies to look for (use exactly these names):\n{fallacy_list}\n\n"
        "Report only fallacies the inferential structure actually exhibits — if a "
        "step is sound, do not invent a defect. For each, give the fallacy name, "
        "the step number it sits at, and a one-sentence explanation of the formal "
        "defect.\n"
        'Reply with ONLY a JSON object: {"findings": [{"fallacy": ..., "step": '
        '<step number>, "explanation": ...}]}. No prose.'
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


def parse_fallacy_response(
    text: str, framework_id: str, steps: list[ReasoningUnit]
) -> FallacyReport:
    """Parse a fallacy response into located findings. Hostile input: unknown
    fallacy names and malformed entries are dropped; an out-of-range/absent step
    leaves the location blank rather than failing."""
    report = FallacyReport(framework_id=framework_id)
    data = _extract_json_object(text)
    if not isinstance(data, dict):
        return report

    for item in data.get("findings") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("fallacy", "")).strip().lower()
        explanation = str(item.get("explanation", "")).strip()
        if name not in _VALID_FALLACIES or not explanation:
            continue

        step_index = _coerce_step(item.get("step"))
        unit = steps[step_index - 1] if step_index and 1 <= step_index <= len(steps) else None
        report.findings.append(
            FallacyFinding(
                fallacy=FallacyType(name),
                explanation=explanation,
                location_text=unit.text if unit else "",
                location_unit_id=unit.id if unit else None,
                step_index=step_index,
            )
        )
    return report


def _coerce_step(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


GenerateFn = Callable[[str, str], str]


def analyse_fallacies(
    framework: Framework,
    units: list[ReasoningUnit],
    *,
    generate: GenerateFn,
    model: str,
    max_steps: int = 20,
) -> FallacyReport:
    steps = number_steps(units, limit=max_steps)
    output = generate(build_fallacy_prompt(framework.title, steps), model)
    return parse_fallacy_response(output, framework.id, steps)


# Fallacies that are genuine ontological *fractures* — a node that cannot be
# coherently placed. Located reasoning, not a model-agreement signal, so (like the
# LLM placement pass) they may legitimately assign CONTRADICTORY_PLACEMENT, which
# the structural scaffold never does. The other fallacies are reasoning defects
# recorded for transparency but do not, by themselves, re-place a node.
_FRACTURING = {FallacyType.CONTRADICTION, FallacyType.CIRCULARITY}


def mark_fallacies(ontology: WorldviewOntology, findings: list[FallacyFinding]) -> int:
    """Annotate ontology nodes with their located fallacies so the
    [coherence metrics](metrics.py) can read them (FR6 → FR7/FR9). Opt-in and
    applied *after* the pure structural scaffold, so the scaffold itself stays
    free of any reasoned/LLM signal.

    Each finding's node gains `metadata['fallacies']` (fallacy + explanation). A
    `contradiction`/`circularity` finding additionally elevates the node to
    `CONTRADICTORY_PLACEMENT` (tagged `placement_source='fallacy'`) so it counts as
    a fracture. Returns the number of findings that located a node.
    """
    marked = 0
    for f in findings:
        nid = f.location_unit_id
        if not nid or nid not in ontology.nodes:
            continue
        node = ontology.nodes[nid]
        node.metadata.setdefault("fallacies", []).append(
            {"fallacy": f.fallacy.value, "explanation": f.explanation}
        )
        if f.fallacy in _FRACTURING:
            node.placement = PlacementState.CONTRADICTORY_PLACEMENT
            node.metadata["placement_source"] = "fallacy"
        marked += 1
    return marked


def make_hoglah_fallacy_analyst(config: HoglahExtractorConfig) -> GenerateFn:
    submitter = make_hoglah_submitter(config)

    def generate(prompt: str, model: str) -> str:
        return submitter.run(prompt, model)

    return generate


def to_jsonable(value: Any) -> Any:
    if isinstance(value, (FallacyReport, FallacyFinding)):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    return value
