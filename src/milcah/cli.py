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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="milcah", description=PURPOSE)
    parser.add_argument("--version", action="version", version=f"milcah {__version__}")
    sub = parser.add_subparsers(dest="command")

    for name, handler, help_text in (
        ("ingest", _cmd_ingest, "Normalise an input into a segmented framework (FR1)."),
        ("extract", _cmd_extract, "Extract typed reasoning units from an input (FR1+FR2)."),
        ("ontology", _cmd_ontology, "Build the worldview ontology tree from an input (FR3)."),
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
        if name in ("extract", "ontology"):
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

    args = parser.parse_args(argv)

    if getattr(args, "func", None) is not None:
        return args.func(args)

    # No subcommand — point to the design.
    print(PURPOSE)
    print("Status: v0.2. Built: ingest (FR1), extract (FR2). See docs/architecture.md.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
