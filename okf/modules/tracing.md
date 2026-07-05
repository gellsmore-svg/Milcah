---
type: Module
title: tracing
description: The env-driven Galeed witness — orchestration.started/completed (one run = one trace) and snapshot.saved events onto the family spine; best-effort, off by default.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/tracing.py
tags: [milcah, module, tracing, galeed]
timestamp: 2026-07-05T00:00:00Z
---

# tracing

Milcah's core is dependency-free and has no config file, so spine emission is
environment-driven: `MILCAH_GALEED_ENABLED=1` (with the `galeed` extra), plus
`MILCAH_GALEED_MONGO_URI` / `MILCAH_GALEED_MONGO_DB` (default the family
`mnemosyne_dev`).

`Witness.emit(...)` sends events through a per-emission Galeed `Tracer`:
`orchestration.started` / `orchestration.completed` bracket each
role-orchestration run (one run = one trace; roles + final coherence metrics
in metadata) and `snapshot.saved` marks `metrics --save` (trace on the
snapshot id). Lazy Mongo resolution is locked, resolved-flag-last (the
unlocked pattern once dropped events under a thread race). Everything is
best-effort — tracing never affects an analysis.
