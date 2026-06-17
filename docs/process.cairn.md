# Milcah's core process, in Cairn

The recursive coherence-pressure-test round, described in
[Cairn](https://github.com/gellsmore-svg/Cairn) (the family's process
meta-language). This both documents the engine and exercises Cairn on a
recursive, multi-LLM, human-in-the-loop process.

## CONTEXT

- **Milcah** pressure-tests a framework for coherence; it does not decide truth.
- **burden symmetry** — every framework gets the *same* challenges; none is
  protected for popularity, authority, maturity, or preference.
- Family: ontology via **Mahalath**, memory via **Tirzah**, LLM execution via
  **Hoglah**.

## REQUIREMENTS

```
R1. Every framework SHALL face identical challenge structures.            [MUST]
    ACCEPTANCE: no exemption path exists in the challenge step.
R2. Uncertainty SHALL be a permitted terminal state; forced certainty is
    forbidden.                                                            [MUST]
R3. Coherence scores SHALL exclude popularity / confidence / institutional
    acceptance.                                                           [MUST]
R4. Rounds SHALL be bounded (convergence / threshold / repeat / review / budget). [MUST]
```

## PROCESS — Formal

```
PROCESS AnalyzeFramework (INPUT: framework; OUTPUT: coherence_report)
  STATE
    units       [scope: process; dir: read/write]  ref: U1   # reasoning units
    ontology    [scope: process; dir: read/write]  ref: U2   # worldview tree (Mahalath)
    debt        [scope: process; dir: read/write]  ref: U3   # explanatory debt + scores
    fractures   [scope: process; dir: write]       ref: U4

  1. MILESTONE FRAME — Ingest the framework and extract reasoning. [LLM, STOCHASTIC, SYNC]
     PURPOSE: turn raw input into typed reasoning units.
     STATE UPDATE: units ← claims/assumptions/commitments/bridges/enthymemes/…
  2. MILESTONE PLACE — Build/validate the worldview ontology.
     CALL Mahalath.BuildOntology(units) → ontology              [EXTERNAL, ASSISTED-BY: LLM] [SATISFIES: —]
     STATE UPDATE: each concept gets a placement state (resolved … contradictory).
  3. MILESTONE PRESSURE — Recursively pressure-test each node.
     ITERATE [UNTIL: round converges OR repeated objections; MAX: round_budget]   [SATISFIES: R4]
       3.1 For each open node:
           RECURSE [BASE: node resolved or atomic; MAX_DEPTH: none-fixed]          # FR4
             Ask: what supports this? what must be true? what does it imply?
             what assumptions exist? what explains them?                           [LLM, STOCHASTIC]
             STATE UPDATE: units += recursive units; ontology updated
       3.2 Generate counter-frameworks + strongest objections (web-assisted).      [LLM, STOCHASTIC, ASSISTED-BY: EXTERNAL]  # FR5
       3.3 Apply identical challenge structures to the framework and its rivals.    [CODE, DETERMINISTIC] [SATISFIES: R1]  # FR8
       3.4 Evaluate each reasoning step for fallacies; record locations.           [LLM, STOCHASTIC] [SATISFIES: —]  # FR6
           STATE UPDATE: fractures += located fallacies
       3.5 Update explanatory debt + coherence metrics (social signals excluded).   [CODE, DETERMINISTIC] [SATISFIES: R3]  # FR7, FR9
           STATE UPDATE: debt ← {local/global coherence, breadth, completeness,
                                 fracture density, uncertainty burden, trend}
       3.6 BREAK [IF: convergence reached OR objection pattern repeats]
  4. MILESTONE REVIEW — surface unresolved states for a human.
     AWAIT [EVENT: human review of fractures + unresolved nodes; TIMEOUT: never]    [HUMAN, ASSISTED-BY: LLM]  # FR11
  5. MILESTONE REPORT — emit the coherence report.                                  [CODE, DETERMINISTIC]
     PURPOSE: make assumptions, fractures, and *better-formed* questions explicit.
  OUTPUT: coherence_report  (visible assumptions, ontology state, fractures,
          symmetric burden, sharpened uncertainty — never a verdict of "truth")
  RISKS: an LLM may smuggle in social bias; R1/R3 + deterministic scoring bound it.

  CONSTRAINTS: permitted terminal states include unresolved, equivalent burden,
  insufficient information, currently indistinguishable. [SATISFIES: R2]
```

## PROCESS — operator profile (rendered view)

```
render-profile: operator

FRAME the framework
  Purpose:  Make a worldview's reasoning and ontology explicit.
  Owner:    Analyst   Assisted by: LLM
  Next:     PLACE

PRESSURE the framework
  Purpose:  Recursively test what must be true for it to stay coherent.
  Owner:    Milcah    Assisted by: LLM + web research
  Iterate until: it converges, repeats its objections, or hits the round budget.
  Outputs:  located fractures, explanatory debt, coherence trend.
  Next:     REVIEW

REVIEW & REPORT
  Purpose:  Hand a human the sharpened, still-honest picture — never a verdict.
  Owner:    Human     Assisted by: LLM
```
