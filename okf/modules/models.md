---
type: Module
title: Data model
description: Framework (a normalised, segmented input), Segment, and ReasoningUnit (a typed unit with dependency edges), plus the SourceType and ReasoningUnitType enums; ids are deterministic content hashes for idempotency.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/models.py
tags: [milcah, models, framework, reasoning-unit]
timestamp: 2026-06-19T00:00:00Z
---

# Data model (`models.py`)

- **`Framework`** — a normalised, segmented input: `id`, `title`, `source_type`,
  `raw_text`, `segments`, `metadata`.
- **`Segment`** — one trimmed chunk of a framework (a paragraph / turn / node).
- **`ReasoningUnit`** — a typed unit of reasoning: `type`
  ([ReasoningUnitType](../concepts/reasoning-units.md)), `text`, `segment_index`,
  `depends_on` (edge ids), `markers` (provenance for *why* it was typed), and
  `metadata`.
- **`SourceType`** — `document`, `book`, `hypothesis`, `argument_tree`,
  `conversation`, `web`, `structured_ontology`.
- **`ReasoningUnitType`** — observation / claim / primitive / assumption /
  commitment / bridge / enthymeme / conclusion.

Ids are **deterministic content hashes**, so re-ingesting the same input yields the
same ids (idempotent storage, stable tests). `to_jsonable` renders models to plain
JSON. Produced by [ingestion](ingestion.md) + [extraction](extraction.md); the
shape designed to be [Tirzah-ingestible](../concepts/sibling-integration.md).
