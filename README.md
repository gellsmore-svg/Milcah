# Milcah — the Coherence Engine

**Milcah** ingests a framework, argument, or worldview and **recursively
pressure-tests it for coherence** — exposing assumptions, equalising explanatory
burden, locating fractures, and sharpening uncertainty — using multi-LLM analysis.

> Its purpose is **not to prove truth.** It is to help people reason more honestly
> and comprehensively: every framework pays the same explanatory cost, and
> *"forced certainty is forbidden."*

The guiding question for anything it examines:

> **What would have to be true for this to remain coherent?**

## Status

**v0.2 — early stages built.** The philosophy and requirements are set, and the
first stages of the engine are real: **ingestion (FR1)** normalises an input into a
segmented framework, **reasoning extraction (FR2)** pulls typed reasoning units out
of it (with single-, per-segment, and **multi-LLM** modes, the last reconciling by
text or by meaning), **ontology construction (FR3)** builds the worldview tree with
placement states, the **recursive reasoner (FR4)** pressure-tests each node with the
five questions, **counter-framework research (FR5)** generates the strongest
objections + competing frameworks, the **round controller (FR11)** drives reason +
challenge in rounds to a termination condition, and the **coherence metrics
(FR7/FR9)** score the result structurally — excluding popularity, confidence, and
institutional acceptance (`milcah ingest` / `extract` / `ontology` / `reason` /
`challenge` / `rounds` / `metrics`).
Extraction runs on a deterministic rule-based baseline by default, or — for
higher-quality typing — on a local LLM executed **through Hoglah**
(`--extractor hoglah`). See [`docs/philosophy.md`](docs/philosophy.md),
[`docs/requirements.md`](docs/requirements.md), and the initial
[`docs/architecture.md`](docs/architecture.md). Milcah's own process is described
in Cairn in [`docs/process.cairn.md`](docs/process.cairn.md).

```bash
milcah extract framework.md                              # deterministic baseline
milcah extract framework.md --json                       # full Framework + units JSON
milcah extract framework.md --extractor hoglah --model gemma4:latest
#   ^ LLM extraction via Hoglah→Ollama (needs a `hoglah run --real` daemon;
#     install with `pip install -e ".[hoglah]"`)
milcah extract framework.md --extractor hoglah --per-segment
#   ^ one extraction job per segment, merged with segment provenance —
#     keeps long frameworks within the model's context window
milcah extract framework.md --extractor hoglah \
  --models gemma4:latest,gemma4:e2b,gemma2:2b
#   ^ multi-LLM: extract with each model, then reconcile by agreement —
#     each unit records how many models agreed and how they voted on its type
milcah extract framework.md --extractor hoglah \
  --models gemma4:latest,gemma4:e2b,gemma2:2b --reconcile semantic
#   ^ semantic reconciliation: merge units by MEANING (embeddings) so phrasing
#     variants count as agreement, not separate units
milcah ontology framework.md                             # FR3: worldview tree
#   ^ build the ontology tree from the units — foundations at the root, with an
#     ontological placement state per node (resolved … contradictory)
milcah ontology framework.md --placement llm --model gemma4:latest
#   ^ a model reasons about placement (incl. contradictions) via Hoglah, instead
#     of the deterministic structural scaffold
milcah reason framework.md --model gemma4:latest --max-depth 1 --max-nodes 10
#   ^ FR4: recursively pressure-test each ontology node with the five questions
#     (what supports / must be true / implies / assumes / explains), bounded by
#     a depth threshold + node budget
milcah challenge framework.md --model gemma4:latest
#   ^ FR5: the strongest objections + competing counter-frameworks, applying the
#     same scrutiny to every framework (burden symmetry)
milcah rounds framework.md --model gemma4:latest --max-rounds 3
#   ^ FR11: drive reason + challenge in rounds, stopping on convergence,
#     repeated objections, the round threshold, or the node budget
milcah metrics framework.md                              # FR7/FR9: coherence metrics
#   ^ structural explanatory-debt + coherence scores — deliberately excluding
#     popularity, confidence, institutional acceptance, and model-agreement
```

## What it does (requirements, in brief)

- **Ingest** frameworks from books, documents, hypotheses, argument trees,
  conversations, and web research.
- **Extract** the reasoning: claims, observations, assumptions, commitments,
  bridges, enthymemes, dependencies, conclusions.
- **Build** the (often implicit) worldview ontology and track each concept's
  placement state (resolved … contradictory).
- **Recurse** on every node — *what supports this? what must be true? what does it
  imply? what assumptions exist? what explains them?* — with no fixed depth.
- **Challenge symmetrically** — identical pressure for every framework, no
  exemptions; generate counter-frameworks and the strongest objections.
- **Locate fallacies** and track **explanatory debt** + **coherence metrics**
  that deliberately exclude popularity, confidence, and institutional acceptance.
- **Preserve unresolved states** — uncertainty is a valid outcome, made *more
  precise*, never collapsed.

## Place in the family

Milcah is the orchestrator and judge of coherence; it stands on its siblings
rather than reimplementing them:

| Sibling | Role |
|---|---|
| [Tirzah](https://github.com/gellsmore-svg/tirzah) | graph memory + retrieval |
| [Mahalath](https://github.com/gellsmore-svg/mahalath) | ontology construction |
| [Hoglah](https://github.com/gellsmore-svg/hoglah) | local-first execution queue |
| [Cairn](https://github.com/gellsmore-svg/Cairn) | the process meta-language used to describe it |

## Develop

```bash
git clone https://github.com/gellsmore-svg/Milcah
cd Milcah
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

## Feedback

This is early. Open a [feedback issue](../../issues/new/choose), and see
[CONTRIBUTING.md](CONTRIBUTING.md). Security: [SECURITY.md](SECURITY.md).

## Knowledge bundle

A machine- and human-readable knowledge map of Milcah's concepts and modules is
published as an [Open Knowledge Format](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
bundle under [`okf/`](okf/index.md) — markdown with YAML frontmatter, linked into a
concept graph.

## License

[Apache License 2.0](LICENSE).
