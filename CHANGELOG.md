# Changelog

## [Unreleased]

## [0.5.2] — 2026-08-21

### Fixed
- ``reason`` / ``challenge`` / ``fallacy`` / ``rounds`` / ``orchestrate`` exit
  2 with ``pip install 'milcah[hoglah]'`` when Hoglah is not installed.

## [0.5.1] — 2026-08-21

### Changed
- Lift the M3 extra cap ``hoglah>=0.10.4,<0.11`` to ``hoglah>=0.10.4`` so
  ``milcah[hoglah]`` co-installs with shipped Hoglah 0.11.0. No recorded
  incompatibility; the cap was precautionary.

## [0.5.0] — 2026-08-08

**Action the 2026-08-08 functional/code review**
([docs/review-2026-08-08.md](docs/review-2026-08-08.md)).

### Fixed
- **H1** — vacuous all-RESOLVED structural placement no longer prints
  `global_coherence: 1.0`; field is suppressed with
  `structural_placement_ratio` + `placement_scaffold` flags; specialist
  confidence becomes `unassessed` when coherence is suppressed
- **H2** — word-boundary markers, earliest match, negation window, discourse
  markers only when little prose precedes them
- **H3** — sentence splitter protects abbreviations / initials (`Dr.`, `Fig.`,
  `e.g.`)
- **H4** — blocked specialist results set `error` / `error_type` and unassessed
  confidence bands
- **M1** — lightweight text fallacy hints so `fallacy_load` is not always 0
- **M2** — strip markdown headings/lists/fences before rule extraction
- **M3** — pin `hoglah>=0.10.4,<0.11`
- **L1** — version tests skip on stale editable installs
- **L2** — add `foundation_ratio` (alias retained as `ontological_completeness`)

### Added
- Adversarial extraction tests (negation, marker collision, abbreviations)
- Opt-in `RUN_HOGLAH_TESTS=1` live extractor smoke

## [0.4.0] — 2026-08-07

### Added
- `validate_against_intent` and `assess_confidence` capabilities + Deborah
  estate handlers (intent_alignment scoring; aggregate confidence bands)
- Manifest Stage-0 metadata for the new tools

## [0.3.2] — 2026-08-07

### Added
- `milcah.deborah.critique_negotiator` — content gate for Deborah slice
  (prefers deborah.runtime.negotiate when installed)

## [0.3.1] — 2026-08-07

### Added
- Stage 0 Keturah fields on `coherence_check` / `critique` (`negotiable`,
  semantics, evidence, cost, failure_modes) when keturah≥0.4 is installed;
  fail-soft on older keturah.

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
