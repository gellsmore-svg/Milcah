---
type: Concept
title: Recursive pressure-testing
description: For each reasoning node, the engine asks five questions — what supports this, what must be true, what does this imply, what assumptions exist, what explains those assumptions — to unbounded depth, terminated by deterministic conditions; every unit and round is stored.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/docs/architecture.md
tags: [milcah, recursion, reasoner, fr4, fr11]
timestamp: 2026-06-19T00:00:00Z
---

# Recursive pressure-testing

The engine's core loop (FR4), applied to every [reasoning unit](reasoning-units.md)
and ontology node, asks five questions:

1. **What supports this?**
2. **What must be true for this to hold?**
3. **What does this imply?**
4. **What assumptions exist here?**
5. **What explains those assumptions?**

Recursion has **no fixed depth**; it terminates on deterministic **round
conditions** (FR11): convergence, a recursion threshold, repeated-objection
patterns, a human-review request, or an exhausted compute budget. Every unit's
scores, ontology state, fractures, assumptions, and unresolved nodes are stored
with a trend over time (FR10).

This is where **multi-LLM** analysis and counter-framework research (FR5) live —
several models pressure-test and reconcile, all under
[burden symmetry](burden-symmetry.md). The reasoner is designed but **not yet
built**; the [extraction](../modules/extraction.md) that feeds it (and its
[Hoglah execution path](../modules/hoglah-extractor.md)) exists today.
