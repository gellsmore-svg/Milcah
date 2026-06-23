"""Role-based multi-LLM orchestration over Hoglah (ADR-001).

Ties Milcah's steps into the four roles ADR-001 fixes, each with its own assigned
model, every call routed through Hoglah:

  - **Proposer**  — the recursive reasoner (FR4): what supports / is implied / assumed.
  - **Challenger** — counter-framework research (FR5): the adversary, objections +
    competing frameworks under burden symmetry.
  - **Fallacy**   — FR6: judges the *form* of each inference, marking located
    fallacies onto the ontology as fractures.
  - **Synthesis** — scores coherence; it places/reconciles and **never forces
    certainty**.

ADR-001 discipline, made concrete here: a role × model is one tagged Hoglah job;
model **diversity is for bias reduction** (different models per role), not voting;
and the orchestrator records role→model provenance for transparency but computes
**no cross-role agreement signal** — disagreement only ever *raises* fractures
(fallacies, polysemy), agreement buys no coherence credit (`metrics.EXCLUDED_SIGNALS`).

Every role step is an injectable seam (defaults built over Hoglah), so the
orchestration is unit-testable offline without a daemon.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable

from milcah.challenge import Challenge, challenge_framework
from milcah.fallacy import FallacyReport, analyse_fallacies, mark_fallacies
from milcah.hoglah_extractor import HoglahExtractorConfig
from milcah.metrics import CoherenceMetrics, compute_metrics
from milcah.models import Framework, ReasoningUnit
from milcah.ontology import WorldviewOntology, build_ontology
from milcah.recursive import ReasoningResult, recurse_reasoning


class Role(str, Enum):
    PROPOSER = "proposer"
    CHALLENGER = "challenger"
    FALLACY = "fallacy"
    SYNTHESIS = "synthesis"


@dataclass
class OrchestrationConfig:
    """Per-role model assignment + Hoglah submission settings (ADR-001)."""

    default_model: str = HoglahExtractorConfig.model
    # role.value -> model; falls back to default_model. Assign DIFFERENT models to
    # proposer vs challenger so their localised corpus biases differ (ADR-001).
    models: dict[str, str] = field(default_factory=dict)
    transport: str = "store"
    db_path: str = HoglahExtractorConfig.db_path
    timeout: float = 180.0
    max_depth: int = 1
    max_nodes: int = 12
    max_claims: int = 8
    max_steps: int = 20

    def model_for(self, role: Role) -> str:
        return self.models.get(role.value, self.default_model)

    def hoglah_config(self, role: Role) -> HoglahExtractorConfig:
        return HoglahExtractorConfig(
            model=self.model_for(role), transport=self.transport,
            db_path=self.db_path, timeout=self.timeout,
        )


@dataclass
class OrchestrationResult:
    ontology: WorldviewOntology
    metrics: CoherenceMetrics
    reasoning: ReasoningResult
    challenge: Challenge
    fallacies: FallacyReport
    roles: dict[str, str] = field(default_factory=dict)  # role -> model (provenance, NOT confidence)
    trace: list[dict[str, Any]] = field(default_factory=list)


# Injectable role seams (defaults built over Hoglah).
ExpandFn = Callable[..., list[ReasoningUnit]]   # proposer: expand(node, framework_id)
GenerateFn = Callable[[str, str], str]          # challenger / fallacy: generate(prompt, model)


def _default_expand(config: OrchestrationConfig) -> ExpandFn:
    from milcah.recursive import make_hoglah_reasoner

    return make_hoglah_reasoner(config.hoglah_config(Role.PROPOSER))


def _default_challenge(config: OrchestrationConfig) -> GenerateFn:
    from milcah.challenge import make_hoglah_challenger

    return make_hoglah_challenger(config.hoglah_config(Role.CHALLENGER))


def _default_fallacy(config: OrchestrationConfig) -> GenerateFn:
    from milcah.fallacy import make_hoglah_fallacy_analyst

    return make_hoglah_fallacy_analyst(config.hoglah_config(Role.FALLACY))


def orchestrate(
    framework: Framework,
    units: list[ReasoningUnit],
    *,
    config: OrchestrationConfig | None = None,
    expand: ExpandFn | None = None,
    challenge: GenerateFn | None = None,
    analyse: GenerateFn | None = None,
) -> OrchestrationResult:
    """Run the four roles in order, each with its assigned model, over Hoglah.

    Pass `expand`/`challenge`/`analyse` to inject the role seams (tests); otherwise
    they are built from `config` over Hoglah. The proposer expands the ontology, the
    challenger contests it, the fallacy analyst marks located fractures, and synthesis
    scores coherence — agreement is never scored, disagreement only raises fractures.
    """
    config = config or OrchestrationConfig()
    roles: dict[str, str] = {}
    trace: list[dict[str, Any]] = []
    ontology = build_ontology(framework.id, units)

    # Proposer (FR4) — expand the worldview.
    proposer_model = config.model_for(Role.PROPOSER)
    reasoning = recurse_reasoning(
        ontology, expand=expand or _default_expand(config),
        max_depth=config.max_depth, max_new_nodes=config.max_nodes,
    )
    ontology = reasoning.ontology
    roles[Role.PROPOSER.value] = proposer_model
    trace.append({"role": "proposer", "model": proposer_model,
                  "generated": reasoning.generated, "stop_reason": reasoning.stop_reason})

    # Challenger (FR5) — the adversary, under burden symmetry.
    challenger_model = config.model_for(Role.CHALLENGER)
    challenge_result = challenge_framework(
        framework, units, generate=challenge or _default_challenge(config),
        model=challenger_model, max_claims=config.max_claims,
    )
    roles[Role.CHALLENGER.value] = challenger_model
    trace.append({"role": "challenger", "model": challenger_model,
                  "objections": len(challenge_result.objections),
                  "counter_frameworks": len(challenge_result.counter_frameworks)})

    # Fallacy analyst (FR6) — judge inference form; located fallacies become fractures.
    fallacy_model = config.model_for(Role.FALLACY)
    fallacies = analyse_fallacies(
        framework, units, generate=analyse or _default_fallacy(config),
        model=fallacy_model, max_steps=config.max_steps,
    )
    marked = mark_fallacies(ontology, fallacies.findings)
    roles[Role.FALLACY.value] = fallacy_model
    trace.append({"role": "fallacy", "model": fallacy_model,
                  "findings": len(fallacies.findings), "marked": marked})

    # Synthesis — score coherence (forced certainty forbidden; agreement excluded).
    synthesis_model = config.model_for(Role.SYNTHESIS)
    metrics = compute_metrics(ontology)
    roles[Role.SYNTHESIS.value] = synthesis_model
    trace.append({"role": "synthesis", "model": synthesis_model,
                  "global_coherence": metrics.global_coherence,
                  "fracture_density": metrics.fracture_density})

    return OrchestrationResult(
        ontology=ontology, metrics=metrics, reasoning=reasoning,
        challenge=challenge_result, fallacies=fallacies, roles=roles, trace=trace,
    )


def to_jsonable(result: OrchestrationResult) -> dict[str, Any]:
    from milcah.challenge import to_jsonable as challenge_json
    from milcah.fallacy import to_jsonable as fallacy_json
    from milcah.metrics import to_jsonable as metrics_json
    from milcah.ontology import to_jsonable as ontology_json

    return {
        "roles": result.roles,
        "trace": result.trace,
        "metrics": metrics_json(result.metrics),
        "challenge": challenge_json(result.challenge),
        "fallacies": fallacy_json(result.fallacies),
        "ontology": ontology_json(result.ontology),
        "reasoning": {"generated": result.reasoning.generated,
                      "stop_reason": result.reasoning.stop_reason},
    }
