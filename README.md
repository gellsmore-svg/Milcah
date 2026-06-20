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

**v0.2 — first component built.** The philosophy and requirements are set, and the
first stage of the engine is real: **ingestion (FR1)** normalises an input into a
segmented framework, and **reasoning extraction (FR2)** pulls typed reasoning units
out of it (`milcah ingest` / `milcah extract`). Extraction runs on a deterministic
rule-based baseline by default, or — for higher-quality typing — on a local LLM
executed **through Hoglah** (`--extractor hoglah`). See [`docs/philosophy.md`](docs/philosophy.md),
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
