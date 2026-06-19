---
type: Module Index
title: Milcah Modules
description: The built code (v0.2) — the data model, ingestion (FR1), reasoning extraction (FR2) with a deterministic baseline and an LLM-via-Hoglah path, and the CLI.
resource: https://github.com/gellsmore-svg/Milcah/tree/main/src/milcah
tags: [milcah, modules, code]
timestamp: 2026-06-19T00:00:00Z
---

# Modules

What exists today (FR1 + FR2); the rest of the engine (FR3–FR11) is
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
- **[CLI](cli.md)** (`cli.py`) — `milcah ingest` / `milcah extract`.
