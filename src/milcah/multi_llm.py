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

from collections import Counter
from dataclasses import replace
from typing import Callable

from milcah.hoglah_extractor import HoglahExtractor, HoglahExtractorConfig
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
    ) -> None:
        deduped = list(dict.fromkeys(models))
        if not deduped:
            raise ValueError("MultiLLMExtractor requires at least one model.")
        self.models = deduped
        self.config = config or HoglahExtractorConfig()
        self.per_segment = per_segment
        self._extract_with = extract_with

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
        return reconcile_extractions(by_model, total_models=len(by_model))
