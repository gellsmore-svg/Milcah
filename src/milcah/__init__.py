"""Milcah — the Coherence Engine.

Recursive, multi-LLM coherence pressure-testing of frameworks and worldviews.
See docs/philosophy.md and docs/requirements.md. This is the v0.2 core engine.
"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    # Single source of truth: read the installed distribution rather than
    # restating the version here, so it cannot drift from pyproject.
    __version__ = _pkg_version("milcah")
except PackageNotFoundError:  # running straight from a source checkout
    __version__ = "0.0.0+source"

__all__ = ["__version__"]
