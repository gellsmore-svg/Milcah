---
type: Module
title: Iterative refinement / persistence (FR10)
description: Persist a framework's analysis as timestamped snapshots (framework, units, ontology, metrics) so a worldview's coherence can be tracked over time as it is re-pressure-tested. Dependency-free JSON store; Tirzah is an optional later backend implementing the same protocol.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/persistence.py
tags: [milcah, persistence, iterative-refinement, trend, fr10]
timestamp: 2026-06-23T00:00:00Z
---

# Persistence (`persistence.py`, FR10)

FR10 ("Iterative Refinement") asks Milcah to store, per framework, its scores,
ontology state, fractures, assumptions, unresolved nodes — and the **trend over
time**. A **`Snapshot`** captures one point-in-time analysis (the
[framework](models.md) + [units](models.md) + [ontology](ontology.md) +
[metrics](metrics.md)); re-running the engine later adds another, and the movement
between them is the trend.

Faithful to Milcah's design, the core is **dependency-free** and the backend is an
injectable seam:

- **`build_snapshot(framework, units, ontology, metrics)`** — assemble a snapshot
  from the live analysis objects (deterministic `snapshot_id`).
- **`Store`** protocol — `save` / `history` / `load`. The default
  **`JsonFileStore`** writes one transparent JSON file per snapshot under
  `<root>/<framework_id>/`. **`MongoStore`** (`store_mongo.py`, the `mongo` extra) is
  the durable backend over the **shared family MongoDB** (where Tirzah's
  `mnemosyne_dev` / Mahalath's `mahalath_dev` also live) — snapshots get their own
  `snapshots` collection rather than being forced through Tirzah's node ingestion.
  `pymongo` is imported lazily, so the core stays dependency-free.
- **`compute_trend(snapshots)`** — the time-ordered series + first→last delta for
  each coherence/debt metric (`global_coherence`, `fracture_density`,
  `uncertainty_burden`, …), so a framework improving or degrading under pressure is
  visible.

CLI: `milcah metrics <file> --save` persists a snapshot; `milcah history <file>`
prints the coherence trend (`global_coherence: 0.5 → 0.8 (↑ 0.3)`). `--store json`
(default, under `~/.milcah/snapshots`) or `--store mongo --mongo-db milcah_dev` for
the shared family DB. The full core (FR1–FR11) is now built.
