# Contributing to Milcah

Milcah is early (v0.2 design). The most useful contributions right now are
**sharpening the philosophy, requirements, and architecture** before code sets
them in stone.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
ruff check src tests   # if you have ruff
```

- Python 3.11+; source under `src/milcah/`, tests under `tests/`.
- Decisions are recorded (append-only) in `docs/architecture-decisions.md`.

## Principles a change must respect

These come straight from [`docs/philosophy.md`](docs/philosophy.md) and are not
negotiable:

- **Equal burden.** No framework is protected for popularity, authority,
  maturity, novelty, or preference.
- **Uncertainty is permitted; forced certainty is forbidden.** Unresolved,
  equivalent-burden, insufficient-information, and indistinguishable are *valid*
  outcomes. Never collapse the uncertainty categories.
- **Observations before frameworks.** Start from observed phenomena where
  possible; frameworks explain observations, they do not own them.
- **Coherence excludes social signals.** Popularity, confidence, and institutional
  acceptance never enter a coherence score.

A change that quietly violates one of these is a bug, however useful it looks.

## Reporting

Feedback and questions: <https://github.com/gellsmore-svg/Milcah/issues>.
Security: report privately — see [SECURITY.md](SECURITY.md).
