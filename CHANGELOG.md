# Changelog

## [Unreleased]

## [0.3.0] — 2026-08-07

### Added
- **Deborah estate adapter** (`milcah.deborah`): `critique` / `coherence_check`
  dispatch for Deborah's thin PLAN interpreter — maps
  :func:`run_specialist` onto a COGNITION **evaluate** product (criteria, scores,
  objections, confidence bands). `deborah_dispatch()` and capability index
  entries for `milcah.critique`.
- Manifest capability **`critique`** — alias of `coherence_check` for Deborah
  PLAN ASSUMES/CALL (`milcah.critique@…`).
- `milcah specialist --extractor rule|hoglah` (#16) — matches library
  `SpecialistConfig.extractor`.

### Fixed
- Regression test for real `orchestrate()` → `specialist_result_from_orchestration`
  path (#13) — guards `reasoning.ontology` claim extraction.
- `JsonFileStore.history` corrupt-snapshot skip covered by test (#18).

## [0.2.x]

### Fixed
- `milcah serve` closes its FR10 store on shutdown, including on Ctrl-C (#15);
  the `--store mongo` path leaked a `MongoClient` for the life of the process.
- `Witness` can now close the lazy `MongoClient` it opens (#17), and does so via
  `atexit` and when `set_witness()` replaces it. An injected db is left alone —
  it belongs to the caller.
- The `save` and `history` commands close their store via `try/finally`, so an
  error mid-command no longer leaks the connection.

### Added
- **Snapshot viewer** — `milcah serve` (default :8791, `web` extra): read-only
  browser over saved FR10 snapshots — framework index, per-framework coherence
  trend with server-rendered SVG sparklines (direction-aware deltas), snapshot
  detail, JSON API. `Store.frameworks()` added to both backends.
- **Family trace spine emission** (`MILCAH_GALEED_ENABLED=1`, `galeed` extra):
  `orchestration.started/completed` (one run = one trace) and `snapshot.saved`
  events — best-effort, off by default.
- **Specialist seam**: `run_planned_specialist` / Milcah-as-specialist delegation
  from Tirzah plans.

### Fixed
- Witness lazy Mongo init thread race that could silently drop events.
