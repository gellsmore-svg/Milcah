---
type: Module
title: Counter-framework research (FR5)
description: Generate the strongest objections to a framework's claims and one or more competing frameworks that explain the same ground — applying the same scrutiny to every framework (burden symmetry). The partner to the recursive reasoner.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/challenge.py
tags: [milcah, challenge, counter-framework, objections, fr5, burden-symmetry]
timestamp: 2026-06-20T00:00:00Z
---

# Counter-framework research (`challenge.py`, FR5)

The partner to the [recursive reasoner](recursive.md): challenge a framework
**symmetrically**. For its claims, generate the **strongest objections** (each a
typed [unit](models.md) naming the claim it targets) and one or more **competing
frameworks** (`CounterFramework`: name + summary + its own typed units). The prompt
explicitly applies the *same scrutiny, no exemptions* — this is where
[burden symmetry](../concepts/burden-symmetry.md) becomes operational.

- **`select_claims`** — the framework's challengeable assertions
  (claim/conclusion/commitment/primitive/assumption), de-duped.
- **`build_challenge_prompt` / `parse_challenge_response`** — the pure LLM seam
  (objections + counter-frameworks; malformed entries dropped, unnamed
  counter-frameworks skipped). Units carry `metadata.role` = `objection` /
  `counter_framework`.
- **`challenge_framework(framework, units, *, generate, model)`** — applies an
  injectable `generate`; **`make_hoglah_challenger`** runs it through Hoglah.

CLI: `milcah challenge <file>`. Live (gemma4:latest, vorton): 3 objections (each
targeting a claim) + 2 structured counter-frameworks ("Weave Model", "Linking
Index Logic"). Web-retrieval-grounded counter-research (per the architecture) and
the **FR11 round controller** (driving reasoner + challenge to convergence) are the
next steps.
