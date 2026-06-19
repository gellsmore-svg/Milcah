---
type: Concept
title: The Coherence Engine
description: Milcah ingests a framework, extracts its reasoning, builds its ontology, and recursively pressure-tests it — exposing assumptions, equalising burden, and sharpening uncertainty — without deciding truth. It measures coherence with metrics that deliberately exclude social signals.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/docs/architecture.md
tags: [milcah, coherence, metrics, epistemics]
timestamp: 2026-06-19T00:00:00Z
---

# The Coherence Engine

Milcah's job is to improve the **honesty and completeness** of inquiry, not to
declare a winner. Given a framework, it:

1. **Ingests** it ([FR1](../modules/ingestion.md)) and **extracts its reasoning**
   into typed [reasoning units](reasoning-units.md) ([FR2](../modules/extraction.md)).
2. **Builds the (often implicit) ontology** of the worldview (FR3, delegating to
   [Mahalath](sibling-integration.md)), tracking each concept's placement state
   (resolved … contradictory).
3. **[Recursively pressure-tests](recursive-pressure-testing.md)** every node
   (FR4), generates counter-frameworks and the strongest objections (FR5), and
   locates fallacies (FR6).
4. **Scores coherence** (FR7/FR9) — explanatory debt, local/global coherence,
   breadth, ontological completeness, fracture density, uncertainty burden — kept
   separate and explicitly **excluding popularity, confidence, and institutional
   acceptance**.

Two invariants make it trustworthy: **[burden symmetry](burden-symmetry.md)** (no
framework is protected) and **preserved uncertainty** (unresolved, equivalent-
burden, insufficient-information, and indistinguishable are valid terminal states —
never collapsed). Steps 2–4 are designed but not yet built; steps 1–2 exist today.
