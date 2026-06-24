"""Diverse per-role model selection for orchestration (ADR-001).

ADR-001 wants **different models per role** — proposer vs challenger especially —
so their localised corpus biases differ and disagreement surfaces as a fracture
rather than being papered over by one model talking to itself. But the operator
rarely wants to name four models by hand, and if they name none the orchestrator
falls back *every* role to a single `default_model` — silently defeating the very
diversity the ADR asks for.

This module closes that gap: ask Hoglah which models actually exist
(`Hoglah.available_models()` — the topology-hiding superset query) and assign a
**distinct** model to each unpinned role, honouring any the operator did pin.

`assign_diverse_models` is pure (inject the available list) so it is fully testable
offline; only `make_hoglah_model_lister` touches a real Hoglah/Ollama, and it is
fail-soft — an unreachable Hoglah yields an empty list, which degrades cleanly to
today's single-`default_model` behaviour rather than erroring.

Diversity is for **bias reduction, never voting** (ADR-001): assigning different
models buys no agreement-confidence; it only widens the lens that can catch a
fracture. See `metrics.EXCLUDED_SIGNALS`.
"""

from __future__ import annotations

from typing import Callable, Iterable, Mapping

# Fixed role order — proposer/challenger lead because their adversarial pairing is
# where distinct corpus bias matters most (FR4 ↔ FR5).
ROLE_ORDER = ("proposer", "challenger", "fallacy", "synthesis")

# Hoglah's available_models() is capability-blind — it lists embedding models too
# (Milcah uses one for semantic reconciliation). Handing an embedder to a reasoning
# role produces garbage, so auto-selection drops names that look like embedders.
# Substring match on the model name; coarse but cheap and override-able by pinning.
EMBEDDING_MARKERS = ("embed", "bge-", "bge_", "nomic-embed")


def filter_reasoning_models(models: Iterable[str]) -> list[str]:
    """Drop models whose name marks them as embedding-only (see EMBEDDING_MARKERS)."""
    return [m for m in models
            if m and not any(mark in m.lower() for mark in EMBEDDING_MARKERS)]


def assign_diverse_models(
    roles: Iterable[str],
    available: Iterable[str],
    *,
    pinned: Mapping[str, str] | None = None,
    default: str,
) -> dict[str, str]:
    """Return a full role→model map giving each *unpinned* role a distinct model.

    Operator-pinned roles are kept verbatim. Remaining roles draw distinct models
    from `available` (excluding any already pinned, so an auto pick never collides
    with a hand-chosen one) in order; when the pool runs dry the leftover roles fall
    back to `default` (the only case a model repeats — unavoidable with too few
    models). An empty `available` degrades to all-`default`, i.e. today's behaviour.
    """
    pinned = dict(pinned or {})
    used = set(pinned.values())
    # Preserve order, drop duplicates and anything already pinned.
    pool: list[str] = []
    for m in available:
        if m and m not in used and m not in pool:
            pool.append(m)

    result: dict[str, str] = {}
    for role in roles:
        if role in pinned:
            result[role] = pinned[role]
        elif pool:
            result[role] = pool.pop(0)
        else:
            result[role] = default
    return result


def make_hoglah_model_lister(
    *, host: str | None = None
) -> Callable[[], list[str]]:
    """Build a lister that returns Hoglah's available models, fail-soft.

    Queries `Hoglah(use_real=True).available_models()` — a topology query against
    Ollama, independent of the job transport (so it works the same whether jobs run
    over the store or a broker). Hoglah is imported lazily (optional `hoglah` extra),
    and any failure (missing dep, unreachable Ollama) yields `[]` so the caller falls
    back to `default_model` instead of crashing the run.
    """

    def _list() -> list[str]:
        try:
            from hoglah import Hoglah

            config = {"ollama_host": host} if host else None
            client = Hoglah(use_real=True, config=config)
            try:
                return list(client.available_models())
            finally:
                close = getattr(client, "close", None)
                if callable(close):
                    close()
        except Exception:
            return []

    return _list
