---
type: Module
title: Hoglah extractor
description: The LLM-backed extractor — reuses the extraction seam but routes the model call through Hoglah → Ollama, durably and at controlled concurrency, over the SQLite store or a Kafka/RabbitMQ/Redis transport; the model call sits behind an injectable submit so it is testable without a daemon.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/hoglah_extractor.py
tags: [milcah, extraction, hoglah, ollama, multi-llm]
timestamp: 2026-06-19T00:00:00Z
---

# Hoglah extractor (`hoglah_extractor.py`)

The **quality path** for [extraction](extraction.md): `HoglahExtractor` reuses the
same seam (`build_extraction_prompt` / `parse_extraction_response`) but routes the
model call through [Hoglah](../concepts/sibling-integration.md) → Ollama, so
extraction runs durably against a separate `hoglah run --real` (or `*-bridge`)
daemon.

- **`HoglahExtractorConfig`** — model (default `gemma4:latest`), timeout, and the
  transport.
- **Transports** — `store` (default: Hoglah client `submit` + `wait`) and
  `kafka` / `rabbitmq` / `redis` (via Hoglah's
  [`MessagingSubmitter`](https://github.com/gellsmore-svg/hoglah/blob/main/okf/modules/messaging-submitter.md)).
- **Injectable `submit(prompt, model) -> output`** — the model call is behind a
  callable, so the extractor is unit-testable without a daemon or broker.

**Per-segment extraction** (`per_segment=True`, CLI `--per-segment`): one
extraction job per [segment](ingestion.md) instead of one for the whole
framework, merged with `segment_index` provenance. The store transport submits
the batch and the daemon runs it at its configured concurrency; this keeps long
frameworks within the model's context window and lets one bad segment fail
without losing the rest.

This is the first concrete **multi-LLM-over-Hoglah** integration
([sibling integration](../concepts/sibling-integration.md)) — the next step is
extracting with several models then reconciling, which is Milcah's
[recursive, multi-LLM core](../concepts/recursive-pressure-testing.md). Selected
from the CLI with `--extractor hoglah` (`--per-segment` for the fan-out).
