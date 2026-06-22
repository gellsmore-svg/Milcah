---
type: Module
title: Logical fallacy analysis (FR6)
description: Evaluate every reasoning step for logical fallacies and store their locations. The prompt makes the model's rhetorical-logic reasoning dominant — judge the form of the inference, not the topic's truth, popularity, or authority — to limit localised corpus bias.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/fallacy.py
tags: [milcah, fallacy, rhetorical-logic, corpus-bias, fr6, burden-symmetry]
timestamp: 2026-06-22T00:00:00Z
---

# Logical fallacy analysis (`fallacy.py`, FR6)

The third sibling of the [recursive reasoner](recursive.md) and the
[challenge](challenge.md): where those expand and contest a framework, this judges
the **form** of its inferences. For each [reasoning step](models.md) it looks for
the FR6 fallacy set — contradiction, circularity, equivocation, special pleading,
appeal to popularity, appeal to authority, category error, false equivalence,
unsupported bridge, hidden commitment — and **stores the location** of each
(`FallacyFinding`: fallacy + explanation + the step it sits at).

**Design directive — make the rhetorical-logic cluster dominant.** Fallacy
detection is a question of argument *structure*, not subject matter. The prompt
therefore tells the model to judge **only the form of the inference** — how each
step follows from its support — and explicitly **not** whether a claim is true,
popular, expert-endorsed, or fashionable: *wide acceptance and authority are not
validity.* Making logical form dominant suppresses **localised corpus bias** (the
model's topical opinions about the particular subject), the same reason popularity
and authority are excluded from the [coherence metrics](metrics.md)
(`EXCLUDED_SIGNALS`) and the same scrutiny [burden symmetry](../concepts/burden-symmetry.md)
demands of every framework.

- **`number_steps`** — the ordered steps to evaluate (shared by builder and parser
  so step numbers resolve back to units).
- **`build_fallacy_prompt` / `parse_fallacy_response`** — the pure LLM seam. Steps
  are shown with their `depends_on` support (`from: …`) so the model sees the
  inference; the parser drops unknown fallacy names and malformed entries, and an
  out-of-range step leaves the location blank rather than failing.
- **`analyse_fallacies(framework, units, *, generate, model)`** — applies an
  injectable `generate`; **`make_hoglah_fallacy_analyst`** runs it through Hoglah.

CLI: `milcah fallacy <file> --max-steps`. Live (gemma4:latest): a popularity/
authority framework → `appeal_to_authority` @step 2 and `unsupported_bridge`
@step 3 (correct form-level defects, with step provenance). Next: feed located
contradictions/circularities into the ontology as fractures for the metrics.
