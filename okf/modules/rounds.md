---
type: Module
title: Round controller (FR11)
description: The long-running coherence loop — drive the recursive reasoner (FR4) and counter-framework challenge (FR5) in rounds, terminating on convergence, a repeated-objection pattern, the round threshold, or the node budget. Guaranteed to stop.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/rounds.py
tags: [milcah, rounds, controller, fr11, convergence]
timestamp: 2026-06-20T00:00:00Z
---

# Round controller (`rounds.py`, FR11)

Ties the [recursive reasoner](recursive.md) (FR4) and
[counter-framework research](challenge.md) (FR5) into **rounds**. Each round
expands the ontology a little (`reason`) and challenges it (`challenge`); the
controller decides whether to keep going.

- **`run_rounds(framework, units, *, reason, challenge, max_rounds, node_budget,
  per_round_nodes)`** — runs the loop and returns a `RoundReport` (per-round
  `new_nodes` / `objections` / `counter_frameworks`, totals, and a `stop_reason`).
  The `reason` / `challenge` steps are **injectable**, so the control logic is
  deterministic and testable without a model.
- **Termination (FR11)** is explicit and guaranteed: **converged** (a round adding
  no new reasoning and no objections), **repeated_objections** (the same objection
  set as an earlier round), **max_rounds** (the recursion threshold), or
  **node_budget** (compute budget exhausted).
- **`make_hoglah_round_steps(config)`** — the real steps through Hoglah; each round
  challenges the *evolving* ontology (its nodes are duck-typed claims).

CLI: `milcah rounds <file> --max-rounds --node-budget --per-round-nodes`. Live
(gemma4:latest): 2 rounds (+3 nodes / 4 objections, then +3 / 5), 4 Hoglah jobs,
stopped at the round threshold. This is the orchestration the philosophy's
"rounds to convergence" describes; the remaining pieces are the coherence
**metrics** (FR6–FR9) and human-review/persistence.
