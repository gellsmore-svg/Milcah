---
type: Concept
title: Reasoning units
description: Reasoning is broken into typed units faithful to the philosophy — observation, claim, primitive (accepted starting point), assumption (temporary support), commitment (required for survival), bridge (mechanism connecting layers), enthymeme (unstated structure), and conclusion — with dependencies as edges.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/docs/philosophy.md
tags: [milcah, reasoning-units, taxonomy, fr2]
timestamp: 2026-06-19T00:00:00Z
---

# Reasoning units

The atom Milcah reasons over. Extraction ([FR2](../modules/extraction.md)) pulls a
framework apart into **typed reasoning units**, a taxonomy faithful to
[`docs/philosophy.md`](https://github.com/gellsmore-svg/Milcah/blob/main/docs/philosophy.md)
("Assumptions Must Become Visible"):

- **observation** — an observed phenomenon (observations precede frameworks;
  frameworks explain them, they do not own them).
- **claim** — a plain declarative assertion.
- **primitive** — an accepted starting point.
- **assumption** — temporary support.
- **commitment** — required for the framework to survive.
- **bridge** — a mechanism connecting layers.
- **enthymeme** — an unstated/implied reasoning step.
- **conclusion** — a derived endpoint.

**Dependencies are edges, not a unit type:** a bridge/conclusion `depends_on` the
unit it follows from. Making assumptions, commitments, and enthymemes **visible**
is the precondition for [recursive pressure-testing](recursive-pressure-testing.md)
and [burden symmetry](burden-symmetry.md). The data shape is the
[models module](../modules/models.md); typing is done by the
[extractors](../modules/extraction.md).
