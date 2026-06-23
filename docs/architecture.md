# Architecture (initial / proposed) — Milcah v0.2

This is a first architecture sketch derived from [`philosophy.md`](philosophy.md)
and [`requirements.md`](requirements.md). It is **proposed**, not built — a frame
for the engine to grow into. Decisions will be recorded (append-only) in
`architecture-decisions.md` as they firm up.

## What Milcah is

Milcah is the **Coherence Engine**: it ingests a framework / argument / worldview,
extracts its reasoning, builds its (often implicit) ontology, then **recursively
pressure-tests** it — exposing assumptions, equalising explanatory burden, and
sharpening uncertainty — *without pretending certainty*. It does not decide truth;
it improves the honesty and completeness of inquiry.

## Position in the family

| Project | Role | Milcah uses it for |
|---|---|---|
| **Tirzah** | graph memory + retrieval | persisting/retrieving reasoning units, ontology nodes, prior rounds (FR3, FR4, FR10) |
| **Mahalath** | ontology builder | constructing/validating worldview trees, placement, polysemy (FR3) |
| **Hoglah** | local-first job queue | running the many LLM calls durably and serially / at controlled concurrency (FR4, FR5) |
| **Cairn** | process meta-language | describing Milcah's own recursive process (`process.cairn.md`) |
| **Milcah** | recursive pressure-testing | the orchestration + scoring + burden symmetry on top |

The principle: Milcah is the *orchestrator and judge of coherence*; it leans on the
siblings for memory, ontology, and execution rather than reimplementing them.

## Components (FR → module)

- **Ingestion** (FR1) — accept books/documents/hypotheses/argument-trees/
  conversations/web/structured-ontology into a normalised `Framework` record.
- **Reasoning extraction** (FR2) — pull claims, observations, assumptions,
  commitments, bridges, enthymemes, dependencies, conclusions into typed
  **reasoning units**.
- **Ontology construction** (FR3) — build the worldview tree (parent/children/
  dependencies/bridges + placement confidence); placement states from the
  philosophy (resolved … contradictory). Delegates to Mahalath where it can.
- **Recursive reasoner** (FR4) — for each node, the five questions (*what supports
  this / must be true / does this imply / assumptions exist / explains those
  assumptions*). Unbounded depth, terminated by FR11, every unit stored (FR10).
- **Counter-framework research** (FR5) — hypothesis-driven generation of
  alternatives / competing frameworks / strongest objections, with web retrieval.
- **Fallacy analysis** (FR6) — evaluate each reasoning step against a fallacy set;
  store locations.
- **Explanatory-debt + coherence metrics** (FR7, FR9) — assumption/bridge/
  unresolved/recursion/dependency load; local & global coherence, breadth,
  ontological completeness, fracture density, uncertainty burden — kept
  **separate** and explicitly **excluding** popularity / institutional acceptance.
- **Burden symmetry** (FR8) — apply the *same* challenge structures to every
  framework; no exemptions (the core principle, enforced mechanically).
- **Round controller** (FR11) — runs rounds to convergence / recursion threshold /
  repeated-objection / human-review / budget; long-running.

## State model (gestures)

- `Framework`, `ReasoningUnit` (typed: primitive/assumption/commitment/bridge/
  enthymeme/…), `OntologyNode` (+ placement state), `Fracture`, `RoundScore`.
- Persistence via Tirzah's store; ontology via Mahalath; nothing collapses the
  uncertainty categories (philosophy: "Never collapse categories").

## Non-negotiable invariants (from the philosophy)

- **Equal burden** — no framework is protected for any reason.
- **Uncertainty is permitted; forced certainty is forbidden** — unresolved,
  equivalent-burden, insufficient-information, and indistinguishable are *valid*
  terminal states.
- **Observations before frameworks** — start from observed phenomena where
  possible; frameworks explain observations, they do not own them.
- **Metrics exclude social signals** — popularity / confidence / institutional
  acceptance never enter a coherence score.

## Open design questions (for ADRs)

- The reasoning-unit + ontology schema, and how much is Mahalath vs. Milcah-local.
- How burden-symmetry challenge structures are represented and applied uniformly.
- ~~Multi-LLM orchestration shape (roles? adversarial pairs?) over Hoglah.~~
  **Resolved by [ADR-001](architecture-decisions.md):** role-based + adversarial
  (proposer ↔ challenger), rhetorical-logic cluster dominant in every role,
  disagreement surfaced as uncertainty — never agreement as confidence.
- Coherence-metric definitions precise enough to be reproducible, not vibes.
- The human-review surface (FR11) and how unresolved states are presented.
