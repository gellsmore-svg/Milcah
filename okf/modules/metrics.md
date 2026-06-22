---
type: Module
title: Coherence metrics (FR7/FR9)
description: Score the worldview ontology structurally — explanatory debt (assumption/bridge/unresolved load, dependency depth) and coherence (global coherence, breadth, ontological completeness, fracture density, uncertainty burden). Deliberately excludes popularity, confidence, institutional acceptance, and model-agreement.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/metrics.py
tags: [milcah, metrics, coherence, explanatory-debt, fr7, fr9]
timestamp: 2026-06-20T00:00:00Z
---

# Coherence metrics (`metrics.py`, FR7/FR9)

`compute_metrics(ontology) -> CoherenceMetrics` scores a worldview by
**structure**, in two families kept separate:

- **Explanatory debt (FR7)** — `assumption_load`, `bridge_load`, `unresolved_load`,
  `dependency_depth`, and `fallacy_load` (located [fallacies](fallacy.md), FR6, when
  marked onto the ontology): what the framework leaves unpaid.
- **Coherence (FR9)** — `global_coherence` (share resolved), `breadth` (distinct
  unit types), `ontological_completeness` (share that are foundations),
  `fracture_density` (contradictory + multiple-candidate placements),
  `uncertainty_burden` (partially-resolved + dependent-on-bridge).

Per [burden symmetry](../concepts/burden-symmetry.md), the metrics **exclude all
social signals** — popularity, confidence, institutional acceptance — and, here,
**model-agreement / consensus** too (a confidence-like signal). Every number comes
from the ontology's types, [placement states](ontology.md), and shape. This is why
the [structural placement scaffold](ontology.md) uses no agreement signals: so the
metrics that read it stay clean. Deterministic and fully testable (`EXCLUDED_SIGNALS`
documents the exclusions).

CLI: `milcah metrics <file>` (add `--placement llm` to score a reasoned placement;
add `--with-fallacies` to run [fallacy analysis](fallacy.md) and fold located
fallacies in — a `contradiction`/`circularity` becomes a fracture, every located
fallacy counts toward `fallacy_load`). Located fallacies are reasoned, not social,
signals, so folding them in keeps the metrics faithful to burden symmetry.
