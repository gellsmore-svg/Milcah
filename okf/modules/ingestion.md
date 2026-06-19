---
type: Module
title: Ingestion (FR1)
description: Normalise an input — text, file, conversation, structured argument — into a Framework with trimmed segments; paragraph segmentation, conversation-by-turn, and source-type inference, with richer per-source parsing layering on later.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/ingestion.py
tags: [milcah, ingestion, fr1]
timestamp: 2026-06-19T00:00:00Z
---

# Ingestion (`ingestion.py`, FR1)

Turns an input into a segmented [`Framework`](models.md):

- **`ingest_text(text, ...)`** — normalise raw text into a framework (title derived
  from the first line if not given).
- **`ingest_file(path, ...)`** — read a file and ingest it; `source_type` inferred
  by extension.
- **`segment_text(...)`** — split into trimmed, non-empty `Segment`s: blank-line
  paragraphs by default, or **one segment per speaker turn** for conversations.

The v0.2 baseline segments on paragraphs/turns; richer per-source parsing
(argument trees, web research, structured ontology) layers on later behind the
same entry points, with `source_type` always recorded so
[extraction](extraction.md) and downstream stages can specialise. This is FR1 of
the [coherence engine](../concepts/coherence-engine.md).
