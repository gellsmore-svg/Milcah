---
type: Project
title: Milcah
description: The Coherence Engine — ingest a framework, argument, or worldview, extract its reasoning, build its ontology, and recursively pressure-test it for coherence with multi-LLM analysis. It judges coherence, not truth.
resource: https://github.com/gellsmore-svg/Milcah
tags: [milcah, coherence, reasoning, epistemics, multi-llm]
timestamp: 2026-06-19T00:00:00Z
---

# Milcah

Milcah is the **Coherence Engine**: it ingests a framework / argument / worldview,
extracts its reasoning, builds its (often implicit) ontology, then **recursively
pressure-tests it for coherence** — exposing assumptions, equalising explanatory
burden, and sharpening uncertainty. Its purpose is **not to prove truth**; it is
to help people reason more honestly and comprehensively.

> Guiding question: **What would have to be true for this to remain coherent?**

This bundle is an [Open Knowledge Format](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
description of Milcah's concepts and (built) modules.

## Status

**v0.2 — first component built.** The philosophy and requirements are set; the
first stage of the engine is real: [ingestion](modules/ingestion.md) (FR1) and
[reasoning extraction](modules/extraction.md) (FR2), with an
[LLM extractor over Hoglah](modules/hoglah-extractor.md). The recursive reasoner,
ontology construction, counter-framework research, and scoring (FR3–FR11) are
designed but not yet built.

## Map

- **[Concepts](concepts/index.md)** — the engine's purpose and invariants: the
  coherence engine, typed reasoning units, burden symmetry, recursive
  pressure-testing, and how Milcah stands on its siblings.
- **[Modules](modules/index.md)** — the built code: the data model, ingestion,
  extraction (rule-based + LLM-via-Hoglah), and the CLI.

License: Apache-2.0. Process described in Cairn in
[`docs/process.cairn.md`](https://github.com/gellsmore-svg/Milcah/blob/main/docs/process.cairn.md).
