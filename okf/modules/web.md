---
type: Module
title: web
description: The read-only FR10 snapshot viewer behind `milcah serve` — framework index, per-framework coherence trend as SVG sparklines, snapshot detail, and a JSON API over the same Store seam as the CLI.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/web.py
tags: [milcah, module, web, viewer, fr10]
timestamp: 2026-07-05T00:00:00Z
---

# web

`create_app(store, store_label)` builds a single-file FastAPI viewer over any
FR10 `Store` (JsonFileStore or MongoStore — the same `--store json|mongo`
flags as `history`). `milcah serve` runs it (default `127.0.0.1:8791`; `web`
extra). Strictly read-only — analysis stays in the CLI.

Pages: the framework index (latest coherence numbers per tracked framework);
the framework page — the FR10 **trend over time** rendered as dependency-free
inline SVG sparklines with direction-aware deltas (coherence up = green,
fracture density up = red) plus the snapshot list; and snapshot detail
(metrics table, unit-type counts, collapsible raw JSON). JSON API:
`/api/frameworks`, `/api/frameworks/{id}/trend`,
`/api/frameworks/{id}/snapshots/{sid}`.

`Store.frameworks()` (added to the protocol and both backends) powers the
index: one row per framework with snapshot count and latest metrics.
