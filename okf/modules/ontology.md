---
type: Module
title: Ontology construction (FR3)
description: Build the worldview tree from reasoning units — foundations at the root, derived claims branching out — assigning each node an ontological placement state (resolved, partially resolved, multiple placement candidates, dependent on unresolved bridge, contradictory). A deterministic structural scaffold; LLM/Mahalath placement is the next step.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/ontology.py
tags: [milcah, ontology, fr3, placement, worldview]
timestamp: 2026-06-20T00:00:00Z
---

# Ontology construction (`ontology.py`, FR3)

Turns a framework's [reasoning units](models.md) into a **worldview ontology**: a
tree of `OntologyNode`s with foundations at the root and derived claims branching
out, each carrying an **ontological placement state** from the
[philosophy](../concepts/coherence-engine.md) (`PlacementState`: resolved /
partially resolved / multiple placement candidates / dependent on unresolved bridge
/ contradictory).

- **`build_ontology(framework_id, units)`** — the deterministic **structural
  scaffold**: a node per unit; the parent is what a unit rests on — an explicit
  `depends_on` edge, else the nearest preceding *more foundational* unit (by a
  type-tier order: observation/primitive → assumption/commitment/claim →
  bridge/enthymeme → conclusion).
- **Placement** is read from the signals already present: a multi-LLM **type
  disagreement** (`type_votes`) → *multiple placement candidates*; resting on a
  bridge → *dependent on unresolved bridge*; an enthymeme or weak
  **consensus** → *partially resolved*; foundations → *resolved*.

`contradictory_placement` is **reserved** for the LLM/debate pass and never
assigned by the scaffold. This is the FR3 baseline (like the rule-based
[extractor](extraction.md) was for FR2); the next step is LLM/Mahalath-driven
placement (debate, contradiction detection), per
[sibling integration](../concepts/sibling-integration.md). CLI: `milcah ontology`.
