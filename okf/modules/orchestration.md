---
type: Module
title: Role-based multi-LLM orchestration (ADR-001)
description: Run Milcah's four roles — Proposer (FR4), Challenger (FR5), Fallacy (FR6), Synthesis — each with its own assigned model, every call over Hoglah. Diversity is for bias reduction (rhetorical-logic dominant in every role), not voting; disagreement only raises fractures, agreement is never scored.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/orchestration.py
tags: [milcah, orchestration, multi-llm, roles, adr-001, hoglah]
timestamp: 2026-06-23T00:00:00Z
---

# Role-based multi-LLM orchestration (`orchestration.py`, ADR-001)

The build-out of [ADR-001](../../docs/architecture-decisions.md): tie Milcah's steps
into four roles, each with its own model, every LLM call over Hoglah.

- **Proposer** — recursive reasoner (FR4): expands the worldview ontology.
- **Challenger** — counter-framework research (FR5): the adversary, objections +
  competing frameworks under burden symmetry.
- **Fallacy** — FR6: judges inference *form*; located fallacies become fractures.
- **Synthesis** — scores coherence ([metrics](metrics.md)); never forces certainty.

**`OrchestrationConfig`** assigns a model per role (`models[role]`, falling back to
`default_model`) — assign *different* models to proposer vs challenger so their
localised corpus biases differ. **`orchestrate(framework, units, *, config, expand,
challenge, analyse)`** runs the four roles in order; the role steps are injectable
seams (defaults built over Hoglah via `make_hoglah_*`), so it is unit-testable
offline. `OrchestrationResult` carries the ontology, metrics, challenge, fallacies,
and a `roles` map (role → model **provenance, not confidence**).

ADR-001 discipline, concrete here: a role × model is one tagged Hoglah job; the
orchestrator computes **no cross-role agreement/consensus signal** (none appears in
`to_jsonable`); disagreement only ever *raises* fractures (fallacies, polysemy),
honouring `metrics.EXCLUDED_SIGNALS` and "forced certainty is forbidden".

CLI: `milcah orchestrate <file> [--proposer-model … --challenger-model … …]`.
Live (diverse models): proposer `gemma4:e2b` → +3 nodes, challenger `gemma2:2b`,
fallacy `gemma4:e2b` → 1 finding, synthesis scores coherence — all four roles over
one Hoglah daemon.
