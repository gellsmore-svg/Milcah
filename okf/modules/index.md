---
type: Module Index
title: Milcah Modules
description: The built code (v0.2) — the data model, ingestion (FR1), reasoning extraction (FR2) with a deterministic baseline and an LLM-via-Hoglah path, and the CLI.
resource: https://github.com/gellsmore-svg/Milcah/tree/main/src/milcah
tags: [milcah, modules, code]
timestamp: 2026-06-19T00:00:00Z
---

# Modules

What exists today: **the full core — FR1–FR11.** The last piece, persistence (FR10),
is built as a dependency-free snapshot store with a Tirzah-backed backend as an
optional later seam.

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
- **[Fallacy analysis](fallacy.md)** (`fallacy.py`) — evaluate each reasoning step
  for logical fallacies, rhetorical-logic reasoning made dominant (FR6).
- **[Round controller](rounds.md)** (`rounds.py`) — drive reason + challenge in
  rounds to a termination condition (FR11).
- **[Coherence metrics](metrics.md)** (`metrics.py`) — structural explanatory-debt
  + coherence scores, excluding social signals (FR7/FR9).
- **[Persistence](persistence.md)** (`persistence.py`) — timestamped snapshots +
  coherence trend over time; dependency-free JSON store (FR10).
- **[CLI](cli.md)** (`cli.py`) — `milcah ingest` / `milcah extract`.
