# Milcah CLI walkthrough

Every `milcah` subcommand in pipeline order, with what each one adds. Moved
from the root README (2026-10). Model-backed steps run through
[Hoglah](https://github.com/gellsmore-svg/hoglah) and need a `hoglah run --real`
worker (`pip install "milcah[hoglah]"`).

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
milcah challenge framework.md --model gemma4:latest --web-search \
  --web-search-url http://localhost:8080 --web-allow-private-search-endpoint
#   ^ ground FR5 in transient, cited web evidence through SearxNG. Recursive
#     reasoning derives a separate bounded query from each node. Web text is
#     marked untrusted and never becomes established knowledge automatically.
milcah rounds framework.md --model gemma4:latest --max-rounds 3
#   ^ FR11: drive reason + challenge in rounds, stopping on convergence,
#     repeated objections, the round threshold, or the node budget
milcah fallacy framework.md --model gemma4:latest --max-steps 20
#   ^ FR6: locate fallacies at reasoning steps, judging inference form rather
#     than institutional acceptance or popularity
milcah orchestrate framework.md --auto-models
#   ^ ADR-001: role-based Proposer/Challenger/Fallacy/Synthesis orchestration;
#     model diversity is provenance and bias reduction, never a confidence score
milcah specialist "Is this framework coherent?" --context-file framework.md --json
#   ^ the public Tirzah↔Milcah coherence_check contract, executable from the CLI
milcah metrics framework.md                              # FR7/FR9: coherence metrics
#   ^ structural explanatory-debt + coherence scores — deliberately excluding
#     popularity, confidence, institutional acceptance, and model-agreement
milcah history framework.md                              # FR10: saved snapshot trend
```
