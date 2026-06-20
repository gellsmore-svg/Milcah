---
type: Module
title: Multi-LLM extraction
description: Extract a framework with several models, then reconcile — group units by normalised text and record how many models agreed (agreement/consensus), which models, and the vote over each unit's type (majority wins, disagreement surfaced). Tolerates per-model failures.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/multi_llm.py
tags: [milcah, multi-llm, reconciliation, consensus]
timestamp: 2026-06-20T00:00:00Z
---

# Multi-LLM extraction (`multi_llm.py`)

Milcah's **core thesis** in its first concrete form: extract the same framework
with several models, then **reconcile** — surfacing agreement and disagreement
rather than trusting one model.

- **`MultiLLMExtractor(models=[...])`** — runs each model through a
  [HoglahExtractor](hoglah-extractor.md) (so it inherits the Hoglah execution path
  and `--per-segment`), then reconciles. **Tolerates per-model failures**: a slow /
  timed-out model is skipped (consensus is computed over the survivors); it raises
  only if *all* models fail.
- **`reconcile_extractions(...)`** — pure and deterministic (unit-testable). Groups
  [reasoning units](../concepts/reasoning-units.md) by normalised text and records,
  per unit: `agreement` (how many models extracted it), `consensus` (the share of
  models), `models`, and `type_votes`. The unit's **type is the majority vote** —
  so when models disagree on a type, the vote is *kept*, not collapsed, in line with
  [burden symmetry](../concepts/burden-symmetry.md) (disagreement made visible).

This is the **multi-LLM-over-Hoglah** integration
([sibling integration](../concepts/sibling-integration.md)) and the substrate the
[recursive pressure-testing](../concepts/recursive-pressure-testing.md) will build
on. CLI: `milcah extract --extractor hoglah --models m1,m2,m3`.

*Current limit:* reconciliation matches on normalised **text**, so phrasing
variants don't merge; **semantic reconciliation** (embeddings or a reconciliation
model) is the next refinement.
