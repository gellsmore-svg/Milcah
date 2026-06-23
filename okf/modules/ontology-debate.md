---
type: Module
title: Delegate ontology debate to Mahalath (FR3)
description: Let Mahalath — the family's multi-agent ontology builder — debate the terms in Milcah's worldview ontology and inform placement. A polysemous term (multiple co-equal senses) can't be cleanly placed; a stale/contested term is unsettled. Faithful to pressure-testing, the delegation only exposes fractures, never resolves one away.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/ontology_debate.py
tags: [milcah, ontology, mahalath, placement, polysemy, fr3]
timestamp: 2026-06-23T00:00:00Z
---

# Delegate ontology debate to Mahalath (`ontology_debate.py`, FR3)

Milcah owns the *structure* of a worldview ([ontology](ontology.md) tree +
[placement states](ontology.md)). Whether a **term** is ontologically settled —
one clean sense, several co-equal senses (polysemy), or a stale/contested
definition — is what **Mahalath** debates. This module delegates that judgment:
for each node, ask Mahalath about the term and let its debated ontology inform
placement.

- **`debate_placement(ontology, resolve)`** — walks the nodes; each node Mahalath
  knows gains `metadata['mahalath']` (MPL label + senses) and, where Mahalath
  exposes a weaker grounding, a **worsened** placement (`placement_source='mahalath'`).
  Mahalath's verdict maps: polysemous → `multiple_placement_candidates`; stale →
  `partially_resolved`; cleanly grounded / unknown → unchanged.
- **Only-worsen rule** — faithful to Milcah's pressure-testing ethos, debate moves a
  node *down* the coherence ladder or leaves it; it can never erase an existing
  fracture (a contradiction stays a contradiction).
- **`make_mahalath_debater(uri, database, language)`** — the real resolver over
  Mahalath's ontology (`mahalath.retrieval.search_terms`). Optional + fail-soft;
  `mahalath`/`pymongo` are the `mahalath` extra, imported lazily — the core stays
  dependency-free.

CLI: `milcah ontology <file> --placement mahalath` (also `milcah metrics`). Live: a
claim about the seeded polysemous term *substrate* (3 senses) → the node moves from
`resolved` to `multiple_placement_candidates`, which then raises `fracture_density`
in the [metrics](metrics.md). The injectable `resolve` keeps it unit-testable offline.
