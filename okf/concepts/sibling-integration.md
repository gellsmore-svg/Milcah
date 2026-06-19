---
type: Concept
title: Sibling integration
description: Milcah is the orchestrator and judge of coherence; it leans on its siblings rather than reimplementing them — Tirzah for graph memory, Mahalath for ontology construction, Hoglah for durable multi-LLM execution, and Cairn to describe its own process.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/docs/architecture.md
tags: [milcah, integration, tirzah, mahalath, hoglah, cairn]
timestamp: 2026-06-19T00:00:00Z
---

# Sibling integration

Milcah is the **orchestrator and judge of coherence**; it stands on its siblings
rather than reimplementing memory, ontology, or execution:

| Sibling | Milcah uses it for |
|---|---|
| **[Tirzah](https://github.com/gellsmore-svg/tirzah/blob/main/okf/index.md)** | persist/retrieve reasoning units, ontology nodes, and prior rounds (FR3/FR4/FR10) |
| **Mahalath** | construct/validate the worldview ontology, placement, polysemy (FR3) |
| **[Hoglah](https://github.com/gellsmore-svg/hoglah/blob/main/okf/index.md)** | run the many LLM calls durably and at controlled concurrency (FR4/FR5) |
| **[Cairn](https://github.com/gellsmore-svg/Cairn)** | describe Milcah's own recursive process (`process.cairn.md`) |

The first concrete integration is live: the
[LLM extractor over Hoglah](../modules/hoglah-extractor.md) routes
[extraction](../modules/extraction.md) through Hoglah → Ollama, and is the seam
where Milcah's **multi-LLM** core (several models reasoning + reconciling) becomes
real — the "multi-LLM orchestration over Hoglah" open ADR. Persistence via Tirzah
and ontology via Mahalath are designed but not yet wired.
