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
        return HoglahExtractor(
            HoglahExtractorConfig(
                model=args.model or HoglahExtractorConfig.model,
                transport=args.transport,
                db_path=args.hoglah_db or HoglahExtractorConfig.db_path,
                timeout=args.timeout,
            )
        )
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
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="milcah", description=PURPOSE)
    parser.add_argument("--version", action="version", version=f"milcah {__version__}")
    sub = parser.add_subparsers(dest="command")

    for name, handler, help_text in (
        ("ingest", _cmd_ingest, "Normalise an input into a segmented framework (FR1)."),
        ("extract", _cmd_extract, "Extract typed reasoning units from an input (FR1+FR2)."),
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
        if name == "extract":
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

    args = parser.parse_args(argv)

    if getattr(args, "func", None) is not None:
        return args.func(args)

    # No subcommand — point to the design.
    print(PURPOSE)
    print("Status: v0.2. Built: ingest (FR1), extract (FR2). See docs/architecture.md.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
