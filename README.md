# Milcah

**Milcah takes a framework, argument or worldview and pressure-tests it for
coherence, recursively, using several LLMs.** It exposes the assumptions the
framework rests on, finds where it fractures, and makes its uncertainty
sharper rather than hiding it. The question it asks of everything:

> **What would have to be true for this to remain coherent?**

Its purpose is **not to prove truth**. It helps people reason more honestly
and comprehensively: every framework pays the same explanatory cost, and
*forced certainty is forbidden*.

## Is it for you?

**Good fit:** you want a structured, symmetric critique of a framework, such
as a book's argument, a hypothesis or a position paper, in which competing
frameworks get the same scrutiny and unresolved questions stay visible.

**Not a fit:** fact-checking, or a single verdict score. Milcah deliberately
keeps popularity, institutional acceptance and model agreement out of its
metrics, and it treats "unresolved" as a valid outcome.

## Try it

```bash
pip install milcah
milcah extract framework.md           # offline: segments the text and types its reasoning units
```

The offline path is a deterministic baseline. The analysis that matters
(placement, recursive reasoning, challenge, fallacies, coherence) runs on
local models through [Hoglah](https://github.com/gellsmore-svg/hoglah):

```bash
pip install "milcah[hoglah]"          # then run a worker: hoglah run --real
milcah orchestrate framework.md --auto-models
```

## What it does, step by step

| Step | Command | Adds |
|---|---|---|
| Extract | `milcah extract` | Claims, observations, assumptions, bridges, enthymemes and conclusions. With `--models a,b,c`, several models extract and their agreement is recorded per unit |
| Build the ontology | `milcah ontology` | The worldview tree, foundations at the root, each node with a placement state (resolved … contradictory) |
| Recurse | `milcah reason` | Each node pressure-tested: what supports it, what must be true, what it implies, what it assumes, what explains it |
| Challenge | `milcah challenge` | The strongest objections and competing frameworks, with the same pressure for every framework; optional cited web evidence via SearxNG |
| Locate fallacies | `milcah fallacy` | Inference defects, judged on form, not on acceptance |
| Iterate | `milcah rounds` | Reason and challenge repeated until convergence, repeated objections or a budget |
| Measure | `milcah metrics`, `milcah history` | Explanatory debt and coherence scores, saved as snapshots over time |
| All of it | `milcah orchestrate` | Proposer, Challenger, Fallacy and Synthesis roles across models |

Full options and examples: [docs/cli.md](docs/cli.md).

## Know before you rely on it

- **Without a model there is no coherence score.** On the deterministic
  default, `metrics` reports explanatory debt but suppresses
  `global_coherence` ("structural scaffold only"). Use
  `--placement llm` (via Hoglah) or `--placement mahalath` for a real one.
- **Agreement between models is provenance, not confidence.** Model
  diversity reduces bias; it is never counted as evidence that a claim is
  true.
- **Web evidence is untrusted.** Search results ground a challenge, are
  cited, and never become established knowledge automatically.

## Viewing and tracing

- `milcah serve` (`pip install "milcah[web]"`, `127.0.0.1:8791`): a read-only
  browser over saved snapshots, with each framework's coherence trend over
  time.
- With `MILCAH_GALEED_ENABLED=1` and the `galeed` extra, orchestration runs
  and snapshot saves emit to [Galeed](https://github.com/gellsmore-svg/galeed),
  viewable in [Mizpah](https://github.com/gellsmore-svg/Mizpah) or with
  `galeed trace`.

## In the family

Milcah stands on its siblings rather than reimplementing them:
[Tirzah](https://github.com/gellsmore-svg/tirzah) for memory and retrieval
(and `milcah specialist` serves Tirzah's coherence-check contract),
[Mahalath](https://github.com/gellsmore-svg/mahalath) for ontology,
[Hoglah](https://github.com/gellsmore-svg/hoglah) for model execution, and
[Deborah](https://github.com/gellsmore-svg/Deborah) for process plans
(`milcah.deborah` plugs critique into them).

## More

- [Philosophy](docs/philosophy.md) · [requirements](docs/requirements.md) ·
  [architecture](docs/architecture.md) and its
  [decisions](docs/architecture-decisions.md) · Milcah's own process in
  [Cairn](docs/process.cairn.md) · [okf/](okf/index.md) concept map.
- The [2026-08-08 review](docs/review-2026-08-08.md) was actioned in 0.5.0
  (see [CHANGELOG](CHANGELOG.md)).
- Develop: `pip install -e ".[dev]" && pytest`.
- This is early: [feedback issues](https://github.com/gellsmore-svg/Milcah/issues/new/choose)
  are welcome. [CONTRIBUTING](CONTRIBUTING.md) · [SECURITY](SECURITY.md) ·
  Apache 2.0, see [LICENSE](LICENSE).
