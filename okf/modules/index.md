---
type: Module Index
title: Milcah Modules
description: The built code (v0.2) — the data model, ingestion (FR1), reasoning extraction (FR2) with a deterministic baseline and an LLM-via-Hoglah path, and the CLI.
resource: https://github.com/gellsmore-svg/Milcah/tree/main/src/milcah
tags: [milcah, modules, code]
timestamp: 2026-06-19T00:00:00Z
---

# Modules

What exists today (FR1–FR5); the rest of the engine (FR6–FR11) is
[designed but not built](../concepts/coherence-engine.md).

- **[Models](models.md)** (`models.py`) — `Framework`, `Segment`, `ReasoningUnit`
  + the type enums.
- **[Ingestion](ingestion.md)** (`ingestion.py`) — normalise an input into a
  segmented framework (FR1).
- **[Extraction](extraction.md)** (`extraction.py`) — typed
  [reasoning units](../concepts/reasoning-units.md) via a deterministic
  rule-based baseline + an LLM seam (FR2).
- **[Hoglah extractor](hoglah-extractor.md)** (`hoglah_extractor.py`) — the LLM
  extractor executed through [Hoglah](../concepts/sibling-integration.md) → Ollama.
- **[Multi-LLM extraction](multi-llm.md)** (`multi_llm.py`) — extract with several
  models, then reconcile by agreement (Milcah's core).
- **[Ontology construction](ontology.md)** (`ontology.py`) — build the worldview
  tree with placement states (FR3).
- **[Recursive reasoner](recursive.md)** (`recursive.py`) — pressure-test each node
  with the five questions, bounded recursion (FR4).
- **[Counter-framework research](challenge.md)** (`challenge.py`) — objections +
  competing frameworks; symmetric challenge (FR5).
- **[CLI](cli.md)** (`cli.py`) — `milcah ingest` / `milcah extract`.
