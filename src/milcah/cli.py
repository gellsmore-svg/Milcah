"""Minimal CLI for Milcah.

The engine itself is not implemented yet (v0.2 is the design foundation). This
entry point exists so the package is real and buildable, and to surface the
project's purpose and pointers. It intentionally does not pretend to analyse
anything.
"""

from __future__ import annotations

import argparse

from milcah import __version__

PURPOSE = (
    "Milcah — the Coherence Engine.\n"
    "Recursively pressure-tests frameworks for coherence; it does not decide truth.\n"
    "Guiding question: 'What would have to be true for this to remain coherent?'\n"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="milcah", description=PURPOSE)
    parser.add_argument("--version", action="version", version=f"milcah {__version__}")
    parser.add_subparsers(dest="command")  # reserved for the engine commands
    parser.parse_args(argv)

    # No engine yet — point to the design.
    print(PURPOSE)
    print("Status: v0.2 design. See docs/philosophy.md, docs/requirements.md, docs/architecture.md.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
