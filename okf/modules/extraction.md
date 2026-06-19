---
type: Module
title: Reasoning extraction (FR2)
description: Pull typed reasoning units from a framework behind one Extractor interface — a deterministic, transparent marker-based RuleBasedExtractor baseline, plus an LLM seam (prompt build + response parse) kept separate from any model call so both are testable.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/extraction.py
tags: [milcah, extraction, fr2, reasoning-units]
timestamp: 2026-06-19T00:00:00Z
---

# Reasoning extraction (`extraction.py`, FR2)

Pulls typed [reasoning units](../concepts/reasoning-units.md) out of a
[`Framework`](models.md), behind one `Extractor` interface
(`extract(framework) -> list[ReasoningUnit]`):

- **`RuleBasedExtractor`** — the deterministic, dependency-free **baseline**:
  marker-based typing per sentence (every typing records the markers that produced
  it) with bridge/conclusion `depends_on` edges. Transparent and fully testable
  offline — the floor, not the ceiling.
- **LLM seam** — `build_extraction_prompt(framework)` + `parse_extraction_response`,
  kept **separate from any model call** so the prompt and parser are testable on
  their own (the same pattern as Tirzah's deep-retrieval planner). Parsing treats
  model output as hostile input: malformed entries skipped, unknown types dropped.

The quality path that backs this seam with a real model is the
[Hoglah extractor](hoglah-extractor.md). This is FR2 of the
[coherence engine](../concepts/coherence-engine.md); its output feeds the (unbuilt)
[recursive reasoner](../concepts/recursive-pressure-testing.md).
