"""Round controller (FR11) — the long-running coherence loop.

Ties the [recursive reasoner](recursive.py) (FR4) and
[counter-framework research](challenge.py) (FR5) into **rounds**: each round
expands the ontology a little and challenges it, and the controller decides
whether to keep going. Termination (FR11) is explicit and guaranteed — it stops on
**convergence** (a round that adds nothing new), a **recursion threshold**
(max rounds), **repeated objection patterns**, or an exhausted **node budget**.

The per-round steps (`reason`, `challenge`) are injectable, so the control logic
is deterministic and testable without any model; `make_hoglah_round_steps` wires
the real steps through Hoglah.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from milcah.challenge import (
    Challenge,
    CounterFramework,
    challenge_framework,
    make_hoglah_challenger,
)
from milcah.hoglah_extractor import HoglahExtractorConfig
from milcah.models import Framework, ReasoningUnit
from milcah.ontology import WorldviewOntology, build_ontology
from milcah.recursive import ReasoningResult, make_hoglah_reasoner, recurse_reasoning


@dataclass
class Round:
    number: int
    new_nodes: int
    objections: int
    counter_frameworks: int


@dataclass
class RoundReport:
    framework_id: str
    ontology: WorldviewOntology
    rounds: list[Round] = field(default_factory=list)
    objections: list[ReasoningUnit] = field(default_factory=list)
    counter_frameworks: list[CounterFramework] = field(default_factory=list)
    stop_reason: str = ""

    @property
    def total_nodes(self) -> int:
        return len(self.ontology.nodes)


ReasonStep = Callable[[WorldviewOntology, int], ReasoningResult]
ChallengeStep = Callable[[Framework, WorldviewOntology], Challenge]


def run_rounds(
    framework: Framework,
    units: list[ReasoningUnit],
    *,
    reason: ReasonStep,
    challenge: ChallengeStep,
    max_rounds: int = 3,
    node_budget: int = 30,
    per_round_nodes: int = 10,
) -> RoundReport:
    """Run coherence rounds (reason → challenge) to termination (FR11)."""
    ontology = build_ontology(framework.id, units)
    report = RoundReport(framework_id=framework.id, ontology=ontology)
    seen_objection_sets: list[frozenset[str]] = []
    generated_total = 0

    for n in range(1, max_rounds + 1):
        remaining = node_budget - generated_total
        if remaining <= 0:
            report.stop_reason = "node_budget"
            break

        result = reason(ontology, min(per_round_nodes, remaining))
        generated_total += result.generated
        ch = challenge(framework, ontology)
        report.objections.extend(ch.objections)
        report.counter_frameworks.extend(ch.counter_frameworks)
        report.rounds.append(
            Round(n, result.generated, len(ch.objections), len(ch.counter_frameworks))
        )

        # convergence: a round that produced no new reasoning and no objections
        if result.generated == 0 and not ch.objections:
            report.stop_reason = "converged"
            break
        # repeated objection pattern: the same objections as an earlier round
        obj_set = frozenset(o.text for o in ch.objections)
        if obj_set and obj_set in seen_objection_sets:
            report.stop_reason = "repeated_objections"
            break
        seen_objection_sets.append(obj_set)

    if not report.stop_reason:
        report.stop_reason = "max_rounds"
    return report


def make_hoglah_round_steps(
    config: HoglahExtractorConfig,
) -> tuple[ReasonStep, ChallengeStep]:
    """The real per-round steps, run through Hoglah."""
    reasoner = make_hoglah_reasoner(config)
    challenger = make_hoglah_challenger(config)

    def reason(ontology: WorldviewOntology, budget: int) -> ReasoningResult:
        return recurse_reasoning(ontology, expand=reasoner, max_depth=1, max_new_nodes=budget)

    def challenge(framework: Framework, ontology: WorldviewOntology) -> Challenge:
        # OntologyNodes are duck-typed claims (they have .type and .text) for
        # select_claims, so the evolving tree is what gets challenged each round.
        return challenge_framework(
            framework, list(ontology.nodes.values()), generate=challenger, model=config.model
        )

    return reason, challenge
