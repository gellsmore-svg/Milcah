"""CLI for Milcah.

The full engine is not built yet (v0.2). What *is* real is the first stage:
`ingest` (FR1) normalises an input into a segmented framework, and `extract`
(FR2) pulls typed reasoning units out of it. With no subcommand, the CLI prints
the project's purpose and pointers.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from milcah import __version__
from milcah.extraction import RuleBasedExtractor, extract
from milcah.hoglah_extractor import HoglahExtractor, HoglahExtractorConfig
from milcah.ingestion import ingest_file, ingest_text
from milcah.models import SourceType, to_jsonable
from milcah.ontology import build_ontology
from milcah.ontology import to_jsonable as ontology_to_jsonable
from milcah.recursive import make_hoglah_reasoner, recurse_reasoning
from milcah.challenge import challenge_framework, make_hoglah_challenger
from milcah.challenge import to_jsonable as challenge_to_jsonable
from milcah.rounds import make_hoglah_round_steps, run_rounds
from milcah.metrics import compute_metrics, to_jsonable as metrics_to_jsonable
from milcah.fallacy import analyse_fallacies, make_hoglah_fallacy_analyst
from milcah.fallacy import to_jsonable as fallacy_to_jsonable

PURPOSE = (
    "Milcah — the Coherence Engine.\n"
    "Recursively pressure-tests frameworks for coherence; it does not decide truth.\n"
    "Guiding question: 'What would have to be true for this to remain coherent?'\n"
)


def _read_source(path: str, source_type: str | None, title: str | None):
    """Ingest from a file path, or from stdin when path is '-'."""
    st = SourceType(source_type) if source_type else None
    if path == "-":
        text = sys.stdin.read()
        return ingest_text(text, title=title, source_type=st or SourceType.DOCUMENT)
    return ingest_file(path, source_type=st, title=title)


def _cmd_ingest(args: argparse.Namespace) -> int:
    framework = _read_source(args.source, args.source_type, args.title)
    if args.json:
        print(json.dumps(to_jsonable(framework), indent=2))
    else:
        print(f"framework {framework.id}: {framework.title}")
        print(f"  source_type: {framework.source_type.value}")
        print(f"  segments: {len(framework.segments)}")
    return 0


def _build_extractor(args: argparse.Namespace):
    """Select the extractor: deterministic rule-based (default) or LLM-via-Hoglah."""
    if getattr(args, "extractor", "rule") == "hoglah":
        cfg = HoglahExtractorConfig(
            model=args.model or HoglahExtractorConfig.model,
            embedding_model=args.embedding_model or HoglahExtractorConfig.embedding_model,
            transport=args.transport,
            db_path=args.hoglah_db or HoglahExtractorConfig.db_path,
            timeout=args.timeout,
        )
        models = [m.strip() for m in (args.models or "").split(",") if m.strip()]
        if models:
            from milcah.multi_llm import MultiLLMExtractor

            return MultiLLMExtractor(
                models, config=cfg, per_segment=args.per_segment,
                reconcile=args.reconcile, similarity_threshold=args.similarity,
            )
        return HoglahExtractor(cfg, per_segment=args.per_segment)
    return RuleBasedExtractor()


def _cmd_extract(args: argparse.Namespace) -> int:
    framework = _read_source(args.source, args.source_type, args.title)
    units = extract(framework, _build_extractor(args))
    if args.json:
        print(
            json.dumps(
                {"framework": to_jsonable(framework), "units": to_jsonable(units)}, indent=2
            )
        )
    else:
        counts = Counter(u.type.value for u in units)
        print(f"framework {framework.id}: {framework.title}")
        print(f"  {len(units)} reasoning units from {len(framework.segments)} segments")
        for type_name, n in sorted(counts.items()):
            print(f"    {type_name}: {n}")
        # Multi-LLM: show how many models agreed per unit (agreement distribution).
        if units and "agreement" in (units[0].metadata or {}):
            agree = Counter(u.metadata["agreement"] for u in units)
            dist = ", ".join(f"{k} model(s): {v}" for k, v in sorted(agree.items(), reverse=True))
            print(f"  agreement: {dist}")
    return 0


def _cmd_ontology(args: argparse.Namespace) -> int:
    framework = _read_source(args.source, args.source_type, args.title)
    units = extract(framework, _build_extractor(args))
    ontology = build_ontology(framework.id, units)
    if getattr(args, "placement", "structural") == "llm":
        from milcah.ontology_placement import make_placement_runner, refine_placement

        cfg = HoglahExtractorConfig(
            model=args.model or HoglahExtractorConfig.model,
            transport=args.transport,
            db_path=args.hoglah_db or HoglahExtractorConfig.db_path,
            timeout=args.timeout,
        )
        ontology = refine_placement(
            ontology, submit=make_placement_runner(cfg), model=cfg.model
        )
    if args.json:
        print(json.dumps({"framework": to_jsonable(framework), "ontology": ontology_to_jsonable(ontology)}, indent=2))
    else:
        print(f"framework {framework.id}: {framework.title}")
        print(f"  {len(ontology.nodes)} nodes, {len(ontology.roots)} root(s)")
        placements = Counter(n.placement.value for n in ontology.nodes.values())
        for state, n in sorted(placements.items()):
            print(f"    {state}: {n}")
        print(ontology.render())
    return 0


def _cmd_reason(args: argparse.Namespace) -> int:
    framework = _read_source(args.source, args.source_type, args.title)
    units = extract(framework, _build_extractor(args))
    ontology = build_ontology(framework.id, units)
    cfg = HoglahExtractorConfig(
        model=args.model or HoglahExtractorConfig.model,
        transport=args.transport,
        db_path=args.hoglah_db or HoglahExtractorConfig.db_path,
        timeout=args.timeout,
    )
    result = recurse_reasoning(
        ontology, expand=make_hoglah_reasoner(cfg),
        max_depth=args.max_depth, max_new_nodes=args.max_nodes,
    )
    if args.json:
        print(json.dumps({
            "framework": to_jsonable(framework),
            "ontology": ontology_to_jsonable(result.ontology),
            "generated": result.generated,
            "stop_reason": result.stop_reason,
        }, indent=2))
    else:
        print(f"framework {framework.id}: {framework.title}")
        print(f"  {result.generated} units generated from {result.expanded_nodes} node(s) "
              f"(stop: {result.stop_reason}); {len(result.ontology.nodes)} nodes total")
        print(result.ontology.render())
    return 0


def _cmd_challenge(args: argparse.Namespace) -> int:
    framework = _read_source(args.source, args.source_type, args.title)
    units = extract(framework, _build_extractor(args))
    cfg = HoglahExtractorConfig(
        model=args.model or HoglahExtractorConfig.model,
        transport=args.transport,
        db_path=args.hoglah_db or HoglahExtractorConfig.db_path,
        timeout=args.timeout,
    )
    challenge = challenge_framework(
        framework, units, generate=make_hoglah_challenger(cfg), model=cfg.model
    )
    if args.json:
        print(json.dumps({"framework": to_jsonable(framework), "challenge": challenge_to_jsonable(challenge)}, indent=2))
    else:
        print(f"framework {framework.id}: {framework.title}")
        print(f"  {len(challenge.objections)} objection(s), {len(challenge.counter_frameworks)} counter-framework(s)")
        if challenge.objections:
            print("Objections:")
            for o in challenge.objections:
                tgt = f"  (targets: {o.metadata.get('targets')})" if o.metadata.get("targets") else ""
                print(f"  - [{o.type.value}] {o.text[:70]}{tgt}")
        for cf in challenge.counter_frameworks:
            print(f"Counter-framework — {cf.name}: {cf.summary[:70]}")
            for u in cf.units:
                print(f"    - [{u.type.value}] {u.text[:64]}")
    return 0


def _cmd_fallacy(args: argparse.Namespace) -> int:
    framework = _read_source(args.source, args.source_type, args.title)
    units = extract(framework, _build_extractor(args))
    cfg = HoglahExtractorConfig(
        model=args.model or HoglahExtractorConfig.model,
        transport=args.transport,
        db_path=args.hoglah_db or HoglahExtractorConfig.db_path,
        timeout=args.timeout,
    )
    report = analyse_fallacies(
        framework, units, generate=make_hoglah_fallacy_analyst(cfg),
        model=cfg.model, max_steps=args.max_steps,
    )
    if args.json:
        print(json.dumps({"framework": to_jsonable(framework), "fallacies": fallacy_to_jsonable(report)}, indent=2))
    else:
        print(f"framework {framework.id}: {framework.title}")
        print(f"  {len(report.findings)} fallacy finding(s)")
        for f in report.findings:
            loc = f" @step {f.step_index}: {f.location_text[:50]}" if f.location_text else ""
            print(f"  - [{f.fallacy.value}]{loc}")
            print(f"      {f.explanation[:80]}")
    return 0


def _cmd_rounds(args: argparse.Namespace) -> int:
    framework = _read_source(args.source, args.source_type, args.title)
    units = extract(framework, _build_extractor(args))
    cfg = HoglahExtractorConfig(
        model=args.model or HoglahExtractorConfig.model,
        transport=args.transport,
        db_path=args.hoglah_db or HoglahExtractorConfig.db_path,
        timeout=args.timeout,
    )
    reason, challenge = make_hoglah_round_steps(cfg)
    report = run_rounds(
        framework, units, reason=reason, challenge=challenge,
        max_rounds=args.max_rounds, node_budget=args.node_budget,
        per_round_nodes=args.per_round_nodes,
    )
    if args.json:
        from milcah.ontology import to_jsonable as onto_json

        print(json.dumps({
            "framework": to_jsonable(framework),
            "rounds": [vars(r) for r in report.rounds],
            "stop_reason": report.stop_reason,
            "total_nodes": report.total_nodes,
            "objections": [to_jsonable(o) for o in report.objections],
            "ontology": onto_json(report.ontology),
        }, indent=2))
    else:
        print(f"framework {framework.id}: {framework.title}")
        print(f"  {len(report.rounds)} round(s), stop: {report.stop_reason}; "
              f"{report.total_nodes} nodes, {len(report.objections)} objection(s) total")
        for r in report.rounds:
            print(f"    round {r.number}: +{r.new_nodes} nodes, {r.objections} objections, "
                  f"{r.counter_frameworks} counter-framework(s)")
    return 0


def _cmd_metrics(args: argparse.Namespace) -> int:
    framework = _read_source(args.source, args.source_type, args.title)
    units = extract(framework, _build_extractor(args))
    ontology = build_ontology(framework.id, units)
    if getattr(args, "placement", "structural") == "llm":
        from milcah.ontology_placement import make_placement_runner, refine_placement

        cfg = HoglahExtractorConfig(
            model=args.model or HoglahExtractorConfig.model, transport=args.transport,
            db_path=args.hoglah_db or HoglahExtractorConfig.db_path, timeout=args.timeout,
        )
        ontology = refine_placement(ontology, submit=make_placement_runner(cfg), model=cfg.model)
    if getattr(args, "with_fallacies", False):
        from milcah.fallacy import mark_fallacies

        cfg = HoglahExtractorConfig(
            model=args.model or HoglahExtractorConfig.model, transport=args.transport,
            db_path=args.hoglah_db or HoglahExtractorConfig.db_path, timeout=args.timeout,
        )
        report = analyse_fallacies(framework, units, generate=make_hoglah_fallacy_analyst(cfg), model=cfg.model)
        mark_fallacies(ontology, report.findings)
    metrics = compute_metrics(ontology)
    if args.json:
        print(json.dumps({"framework": to_jsonable(framework), "metrics": metrics_to_jsonable(metrics)}, indent=2))
    else:
        m = metrics_to_jsonable(metrics)
        print(f"framework {framework.id}: {framework.title}")
        print("  explanatory debt (FR7):")
        for k in ("assumption_load", "bridge_load", "unresolved_load", "dependency_depth", "fallacy_load"):
            print(f"    {k}: {m[k]}")
        print("  coherence (FR9):")
        for k in ("global_coherence", "breadth", "ontological_completeness", "fracture_density", "uncertainty_burden"):
            print(f"    {k}: {m[k]}")
        print("  (excludes popularity / confidence / institutional acceptance / model-agreement)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="milcah", description=PURPOSE)
    parser.add_argument("--version", action="version", version=f"milcah {__version__}")
    sub = parser.add_subparsers(dest="command")

    for name, handler, help_text in (
        ("ingest", _cmd_ingest, "Normalise an input into a segmented framework (FR1)."),
        ("extract", _cmd_extract, "Extract typed reasoning units from an input (FR1+FR2)."),
        ("ontology", _cmd_ontology, "Build the worldview ontology tree from an input (FR3)."),
        ("reason", _cmd_reason, "Recursively pressure-test the ontology nodes (FR4)."),
        ("challenge", _cmd_challenge, "Generate objections + counter-frameworks (FR5)."),
        ("fallacy", _cmd_fallacy, "Analyse reasoning steps for logical fallacies (FR6)."),
        ("rounds", _cmd_rounds, "Run coherence rounds (reason + challenge) to convergence (FR11)."),
        ("metrics", _cmd_metrics, "Compute structural coherence metrics (FR7/FR9)."),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("source", help="Path to the input file, or '-' for stdin.")
        p.add_argument(
            "--source-type",
            choices=[t.value for t in SourceType],
            default=None,
            help="Override the inferred source type.",
        )
        p.add_argument("--title", default=None, help="Override the framework title.")
        p.add_argument("--json", action="store_true", help="Emit JSON.")
        p.set_defaults(func=handler)
        if name == "reason":
            p.add_argument("--max-depth", type=int, default=1, help="recursion depth threshold (FR11).")
            p.add_argument("--max-nodes", type=int, default=12, help="generated-node budget (FR11).")
        if name == "fallacy":
            p.add_argument("--max-steps", type=int, default=20, help="max reasoning steps to evaluate (FR6).")
        if name == "metrics":
            p.add_argument(
                "--with-fallacies",
                action="store_true",
                help="run fallacy analysis (FR6) and fold located fallacies into the metrics.",
            )
        if name == "rounds":
            p.add_argument("--max-rounds", type=int, default=3, help="recursion threshold: max rounds (FR11).")
            p.add_argument("--node-budget", type=int, default=30, help="total generated-node budget (FR11).")
            p.add_argument("--per-round-nodes", type=int, default=10, help="node budget per round.")
        if name in ("extract", "ontology", "reason", "challenge", "fallacy", "rounds", "metrics"):
            p.add_argument(
                "--extractor",
                choices=["rule", "hoglah"],
                default="rule",
                help="rule = deterministic baseline; hoglah = LLM via Hoglah/Ollama.",
            )
            p.add_argument("--model", default=None, help="Model for --extractor hoglah.")
            p.add_argument(
                "--transport",
                choices=["store", "kafka", "rabbitmq", "redis"],
                default="store",
                help="Hoglah submission transport for --extractor hoglah.",
            )
            p.add_argument("--hoglah-db", default=None, help="Hoglah SQLite db (store transport).")
            p.add_argument("--timeout", type=float, default=180.0, help="Per-job timeout (s).")
            p.add_argument(
                "--per-segment",
                action="store_true",
                help="hoglah: one extraction job per segment (provenance + long-framework safe).",
            )
            p.add_argument(
                "--models",
                default=None,
                help="hoglah: comma-separated models for multi-LLM extraction "
                "(extract with each, then reconcile by agreement).",
            )
            p.add_argument(
                "--reconcile",
                choices=["text", "semantic"],
                default="text",
                help="multi-LLM: 'text' (exact) or 'semantic' (merge by meaning via embeddings).",
            )
            p.add_argument(
                "--embedding-model",
                default=None,
                help="semantic reconcile: Ollama embedding model (default bge-m3:latest).",
            )
            p.add_argument(
                "--similarity",
                type=float,
                default=0.82,
                help="semantic reconcile: cosine threshold for merging units (default 0.82).",
            )
        if name in ("ontology", "metrics"):
            p.add_argument(
                "--placement",
                choices=["structural", "llm"],
                default="structural",
                help="placement: 'structural' (deterministic scaffold) or 'llm' "
                "(a model assigns placement states, incl. contradictions, via Hoglah).",
            )

    args = parser.parse_args(argv)

    if getattr(args, "func", None) is not None:
        return args.func(args)

    # No subcommand — point to the design.
    print(PURPOSE)
    print("Status: v0.2. Built: ingest (FR1), extract (FR2). See docs/architecture.md.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
