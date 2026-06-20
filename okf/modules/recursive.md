---
type: Module
title: Recursive reasoner (FR4)
description: Pressure-test each ontology node with the five questions — what supports this, what must be true, what does it imply, what assumptions does it rest on, what explains those — generating new typed units that expand the tree, with bounded recursion (depth threshold + node budget) that guarantees termination.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/recursive.py
tags: [milcah, recursion, reasoner, fr4, fr11]
timestamp: 2026-06-20T00:00:00Z
---

# Recursive reasoner (`recursive.py`, FR4)

Milcah's [core loop](../concepts/recursive-pressure-testing.md): for each node in
the [ontology tree](ontology.md), ask the **five questions** (keyed by the relation
each answer bears to the node) —

- `supports` — what supports this? · `must_be_true` — what must be true for it to
  hold? · `implies` — what does it imply? · `assumptions` — what does it rest on? ·
  `explains` — what explains those assumptions?

— generating new typed [reasoning units](models.md) that attach to the node
(placement *partially_resolved* — generated, not yet established) and expand the
tree.

- **`build_reasoning_prompt` / `parse_reasoning_response`** — the pure LLM seam:
  units are tagged with their `relation`, `source_node`, and `generated` flag;
  malformed entries / unknown relations and types are dropped.
- **`recurse_reasoning(ontology, *, expand, max_depth, max_new_nodes)`** —
  breadth-first expansion, deterministic given an injectable `expand`. **Bounded
  recursion is FR11**: it stops on the depth threshold or the new-node budget,
  whichever first, and is guaranteed to terminate (returns a `stop_reason`).
- **`make_hoglah_reasoner(config)`** — runs the questions through Hoglah → Ollama.

CLI: `milcah reason <file> --max-depth --max-nodes`. Live: a single claim ("matter
is stable topological form") expanded into 10 units — supporting observations,
implied conclusions, and **surfaced hidden assumptions** (topology's universal
applicability), exactly the philosophy's "make assumptions visible". The next steps
are counter-framework research (FR5) and the full round controller (FR11).
