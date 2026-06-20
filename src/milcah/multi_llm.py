"""Multi-LLM reasoning extraction (Milcah's core).

Extract the same framework with several models, then **reconcile**: group the
units by what was extracted (normalised text), record how many models agreed and
how each typed it, and surface that as an agreement/consensus signal on every
unit. This is the first concrete step of Milcah's multi-LLM thesis — several
models reasoning over the same input, with **disagreement made visible** rather
than hidden (the type vote is kept, not collapsed).

`reconcile_extractions` is pure and deterministic (unit-testable); the per-model
extraction is the LLM part, run through Hoglah by `MultiLLMExtractor`.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import replace
from typing import Callable

from milcah.hoglah_extractor import (
    HoglahExtractor,
    HoglahExtractorConfig,
    make_hoglah_embedder,
)
from milcah.models import Framework, ReasoningUnit


def _norm(text: str) -> str:
    """Normalise unit text for agreement matching: case- and whitespace-folded,
    trailing punctuation stripped, so "Particles persist." == "particles persist"."""
    return " ".join(text.lower().split()).strip(" .!?;:,")


def reconcile_extractions(
    extractions_by_model: dict[str, list[ReasoningUnit]],
    *,
    total_models: int | None = None,
) -> list[ReasoningUnit]:
    """Merge per-model extractions into a consensus set.

    Units are grouped by normalised text. Each result records how many models
    extracted it (`agreement`), the share of all models (`consensus`), which
    `models`, and the `type_votes` — its type is the **majority vote** (ties
    broken by first-seen, deterministically). Sorted by agreement, descending.
    """
    total = total_models if total_models is not None else len(extractions_by_model)
    groups: dict[str, dict] = {}
    for model, units in extractions_by_model.items():
        counted: set[str] = set()
        for u in units:
            key = _norm(u.text)
            if not key:
                continue
            g = groups.setdefault(key, {"rep": u, "models": set(), "types": Counter()})
            g["types"][u.type] += 1
            if key not in counted:  # count each model at most once per text
                g["models"].add(model)
                counted.add(key)

    reconciled: list[ReasoningUnit] = []
    for g in groups.values():
        rep = g["rep"]
        agreement = len(g["models"])
        majority_type = g["types"].most_common(1)[0][0]
        reconciled.append(
            ReasoningUnit.make(
                framework_id=rep.framework_id,
                unit_type=majority_type,
                text=rep.text,
                segment_index=rep.segment_index,
                markers=["multi-llm"],
                metadata={
                    "agreement": agreement,
                    "consensus": round(agreement / total, 3) if total else 0.0,
                    "models": sorted(g["models"]),
                    "type_votes": {
                        t.value: n for t, n in sorted(g["types"].items(), key=lambda kv: kv[0].value)
                    },
                },
            )
        )
    reconciled.sort(key=lambda u: (-u.metadata["agreement"], u.text.lower()))
    return reconciled


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _mean(vecs: list[list[float]]) -> list[float]:
    if not vecs:
        return []
    dim = len(vecs[0])
    n = len(vecs)
    return [sum(v[i] for v in vecs) / n for i in range(dim)]


def reconcile_semantic(
    extractions_by_model: dict[str, list[ReasoningUnit]],
    *,
    embed: Callable[[str], list[float]],
    threshold: float = 0.82,
    total_models: int | None = None,
) -> list[ReasoningUnit]:
    """Reconcile by **meaning** instead of exact text: cluster units whose text
    embeddings are within `threshold` cosine similarity (greedy, deterministic),
    so phrasing variants merge ("a vorton…" and "vorton…" become one). Each
    cluster yields one unit with the same agreement / consensus / models /
    type_votes signals as `reconcile_extractions`; its representative text is the
    cluster's most frequent (then longest) wording. `embed(text) -> vector` is
    injectable; a unit whose text fails to embed forms its own singleton cluster.
    """
    total = total_models if total_models is not None else len(extractions_by_model)
    clusters: list[dict] = []
    for model, units in extractions_by_model.items():
        for u in units:
            text = u.text.strip()
            if not text:
                continue
            vec = embed(text) or []
            best = None
            best_sim = threshold
            if vec:
                for c in clusters:
                    sim = _cosine(vec, c["centroid"])
                    if sim > best_sim:
                        best, best_sim = c, sim
            if best is None:
                clusters.append(
                    {
                        "rep": u,
                        "models": {model},
                        "types": Counter([u.type]),
                        "texts": Counter([u.text]),
                        "vecs": [vec] if vec else [],
                        "centroid": vec,
                    }
                )
            else:
                best["models"].add(model)
                best["types"][u.type] += 1
                best["texts"][u.text] += 1
                if vec:
                    best["vecs"].append(vec)
                    best["centroid"] = _mean(best["vecs"])

    reconciled: list[ReasoningUnit] = []
    for c in clusters:
        rep_text = max(c["texts"].items(), key=lambda kv: (kv[1], len(kv[0])))[0]
        agreement = len(c["models"])
        majority_type = c["types"].most_common(1)[0][0]
        reconciled.append(
            ReasoningUnit.make(
                framework_id=c["rep"].framework_id,
                unit_type=majority_type,
                text=rep_text,
                segment_index=c["rep"].segment_index,
                markers=["multi-llm", "semantic"],
                metadata={
                    "agreement": agreement,
                    "consensus": round(agreement / total, 3) if total else 0.0,
                    "models": sorted(c["models"]),
                    "type_votes": {
                        t.value: n for t, n in sorted(c["types"].items(), key=lambda kv: kv[0].value)
                    },
                },
            )
        )
    reconciled.sort(key=lambda u: (-u.metadata["agreement"], u.text.lower()))
    return reconciled


PerModelExtract = Callable[[Framework, str], list[ReasoningUnit]]


class MultiLLMExtractor:
    """Extract with several models, then reconcile (Milcah's multi-LLM core).

    Each model's extraction runs through a `HoglahExtractor` (so it inherits the
    Hoglah execution path and per-segment option); the per-model call is behind an
    injectable `extract_with(framework, model)` so the reconciliation is testable
    without any model.
    """

    def __init__(
        self,
        models: list[str],
        *,
        config: HoglahExtractorConfig | None = None,
        per_segment: bool = False,
        extract_with: PerModelExtract | None = None,
        reconcile: str = "text",
        similarity_threshold: float = 0.82,
        embed: Callable[[str], list[float]] | None = None,
    ) -> None:
        deduped = list(dict.fromkeys(models))
        if not deduped:
            raise ValueError("MultiLLMExtractor requires at least one model.")
        if reconcile not in ("text", "semantic"):
            raise ValueError(f"reconcile must be 'text' or 'semantic', got {reconcile!r}.")
        self.models = deduped
        self.config = config or HoglahExtractorConfig()
        self.per_segment = per_segment
        self._extract_with = extract_with
        self.reconcile = reconcile
        self.similarity_threshold = similarity_threshold
        self._embed = embed

    def _extract_model(self, framework: Framework, model: str) -> list[ReasoningUnit]:
        if self._extract_with is not None:
            return self._extract_with(framework, model)
        cfg = replace(self.config, model=model)
        return HoglahExtractor(cfg, per_segment=self.per_segment).extract(framework)

    def extract(self, framework: Framework) -> list[ReasoningUnit]:
        # Tolerate per-model failures (a slow/failed model is skipped, not fatal):
        # one model timing out must not lose the others. Consensus is computed over
        # the models that actually contributed.
        by_model: dict[str, list[ReasoningUnit]] = {}
        failures: list[str] = []
        for model in self.models:
            try:
                by_model[model] = self._extract_model(framework, model)
            except Exception as exc:  # noqa: BLE001 - any model error is non-fatal here
                failures.append(f"{model}: {exc}")
        if not by_model:
            raise RuntimeError(
                f"all {len(self.models)} model(s) failed: {'; '.join(failures)}"
            )
        if self.reconcile == "semantic":
            embed = self._embed or make_hoglah_embedder(self.config)
            return reconcile_semantic(
                by_model, embed=embed, threshold=self.similarity_threshold,
                total_models=len(by_model),
            )
        return reconcile_extractions(by_model, total_models=len(by_model))
