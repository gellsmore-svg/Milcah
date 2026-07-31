"""`milcah.__version__` must not drift from the packaged version.

Hanani shipped a hand-maintained literal that sat at 0.1.0 while the package
was 0.8.0 — it fed `--version` and the Keturah manifest, so the wrong number
was advertised to every MCP consumer. Deriving from importlib.metadata makes
pyproject the single source of truth; this pins that.
"""

from __future__ import annotations

import re
import tomllib
from importlib.metadata import version as pkg_version
from pathlib import Path

import milcah


def test_version_matches_the_installed_distribution():
    assert milcah.__version__ == pkg_version("milcah")


def test_version_matches_pyproject():
    """Guards the other direction: bumping pyproject must be all it takes."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    declared = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    assert milcah.__version__ == declared


def test_version_is_not_a_hardcoded_literal():
    """The regression itself: no version string restated in __init__.py."""
    source = Path(milcah.__file__).read_text(encoding="utf-8")
    assert not re.search(r'^__version__\s*=\s*["\']\d+\.\d+', source, re.M), (
        "__version__ is hardcoded again — derive it from importlib.metadata so "
        "it cannot drift from pyproject."
    )
