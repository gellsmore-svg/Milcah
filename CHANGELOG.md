# Changelog

## [Unreleased]

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
