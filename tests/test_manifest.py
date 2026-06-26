from keturah import validate_manifest

from milcah.contract import SPECIALIST_MODES
from milcah.manifest import build_manifest


def test_manifest_conforms_and_is_built_from_the_contract():
    m = build_manifest()
    assert validate_manifest(m) == []
    assert m.product == "milcah"
    cc = next(c for c in m.capabilities if c.name == "coherence_check")
    # schema enum is sourced from the live contract, not duplicated
    assert set(cc.input_schema["properties"]["mode"]["enum"]) == set(SPECIALIST_MODES)


def test_manifest_exposes_an_mcp_tool():
    assert "coherence_check" in [t["name"] for t in build_manifest().to_mcp()["tools"]]
