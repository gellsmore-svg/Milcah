# Architecture Decisions

Last updated: 2026-06-23

An **Architecture Decision Record** (the `ADR-NNN` rows below) is one design
decision and the reasoning behind it. The `ADR` prefix is a stable ID stamped on
each decision and referenced elsewhere. Records are append-only — if a decision is
reversed, add a new one and note the supersession in both, rather than editing the
old. Milcah's ADR numbers are its own; they do not align with the siblings' numbers.

## Accepted Decisions

| ID | Decision | Resolves |
|---|---|---|
| ADR-001 | Multi-LLM orchestration over Hoglah is **role-based and adversarial**, with the **rhetorical-logic cluster invoked as the dominant cluster** in every role, and **disagreement surfaced as uncertainty — never agreement as confidence**. | `architecture.md` open question: "Multi-LLM orchestration shape (roles? adversarial pairs?) over Hoglah." |

---

## ADR-001 — Multi-LLM orchestration over Hoglah

**Status:** accepted (2026-06-23).

### Context

Milcah's pipeline fans out into many LLM calls: the recursive reasoner asks the
five questions of every node (FR4, `recursive.py`), counter-framework research
generates objections + competing frameworks (FR5, `challenge.py`), fallacy analysis
judges every reasoning step (FR6, `fallacy.py`), and the round controller drives
these to convergence (FR11, `rounds.py`). Extraction already runs multi-model
(`multi_llm.py`: `MultiLLMExtractor` + text/semantic reconciliation), and every LLM
call already routes through Hoglah (`hoglah_extractor.py`) with validated transports
(`store`, plus the `kafka` / `rabbitmq` / `redis` brokers).

The open question (architecture.md) was the *shape* of multi-LLM orchestration:
roles? adversarial pairs? And how it sits on Hoglah. Two of Milcah's load-bearing
constraints make the naive answer wrong:

1. **Model agreement is not a coherence signal.** `metrics.EXCLUDED_SIGNALS`
   already bars popularity / confidence / institutional acceptance **and**
   `model_agreement`. So "run N models and take the majority" cannot be the design —
   a vote would smuggle popularity back in as truth.
2. **Forced certainty is forbidden** (philosophy); burden symmetry applies the same
   scrutiny to every framework. Orchestration must *expose* where reasoning is
   unsettled, not paper over it with a consensus number.

### Decision

**Role-based, adversarial multi-LLM orchestration over Hoglah**, with three rules:

1. **Roles, not a flat vote.** Milcah's steps already are roles; orchestration names
   them and assigns models per role:
   - **Proposer** — the recursive reasoner (FR4): what supports / must be true /
     is implied / assumed.
   - **Challenger** — counter-framework research (FR5): the *adversary*, generating
     the strongest objections and competing frameworks under burden symmetry.
   - **Fallacy analyst** — FR6: judges the *form* of each inference.
   - **Synthesis** — reconciles and *places* (ontology), surfaces fractures, and
     **never forces certainty**. It is a judge of *coherence*, not of truth.
   Adversarial pairing is the **proposer ↔ challenger** relationship, not N copies of
   one prompt voting. The adversary is structural (FR5), already built.

2. **The rhetorical-logic cluster is the dominant cluster in every role.** Per the
   operator directive (2026-06-22, first applied in FR6): every role's prompt judges
   the *form* of the inference — not whether a claim is true, popular,
   expert-endorsed, or fashionable. This is the lever that makes multi-LLM worth
   doing at all: different models carry different *localised corpus biases*; forcing
   each into rhetorical-logic-dominant mode, across diverse models, limits any single
   model's topical prior. Diversity is for **bias reduction**, not for voting.

3. **Disagreement is surfaced as uncertainty; agreement is never promoted to
   confidence.** Reconciliation (`reconcile_extractions` / `reconcile_semantic`)
   already records where models/roles diverge. That divergence is *signal* — it maps
   to `partially_resolved` / `multiple_placement_candidates` (a fracture), exactly
   like Mahalath-delegated polysemy (`ontology_debate.py`). It does **not** feed any
   coherence score (ADR honours `EXCLUDED_SIGNALS`). Where roles agree, the score is
   unchanged — agreement buys no coherence credit.

**On Hoglah:** a role × model pair is one Hoglah job (the job carries `model`; the
role is a job tag). **Serialisation is the point** — Hoglah exists to run the many
LLM calls one at a time on resource-constrained hardware, and the roles run
*sequentially* (proposer → challenger → fallacy → synthesis). The `store` transport
is the default. The broker transports (`kafka`/`rabbitmq`/`redis` via
`MessagingSubmitter`) are **not** a parallelism feature: they buy **durability and
decoupling** — submit and walk away, the daemon executes when it can, results
survive restarts, and work can be handed to a separate worker if you ever run one —
execution stays serialised per worker. No new execution machinery is required; this
ADR is an *orchestration shape* over the already-validated submission layer.

### Consequences

- **Builds on what exists:** `multi_llm.py` (per-model jobs + reconciliation) and
  the Hoglah transports already provide the substrate; the remaining work is naming
  roles, assigning diverse models per role, and routing each as a tagged job.
- **Model-diversity policy:** prefer models from *different* families/corpora for
  proposer vs. challenger so their localised biases differ; pin the
  rhetorical-logic-dominant prompt across all roles. "More models" never means "more
  confident."
- **Coherence stays clean:** because agreement is excluded and disagreement only ever
  *raises* uncertainty/fractures, multi-LLM orchestration cannot inflate a coherence
  score — it can only expose more of the truth about a framework's coherence.
- **Synthesis seam shared with Tirzah:** the Synthesis role is the natural place to
  adopt a frontier `synthesis_model` (the Tirzah ↔ Milcah bridge noted in
  `.restart.md`) — a stronger model writing the final reconciliation over a fuller
  context, still forbidden from forcing certainty.
- **Open follow-ons:** per-role model-assignment config. A broker transport may be
  chosen for *durability* (submit-and-walk-away, restart survival), but **not** for
  parallelism — roles run serially through Hoglah by design.
