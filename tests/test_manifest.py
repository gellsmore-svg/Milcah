from keturah import validate_manifest

from milcah.contract import REQUEST_FIELDS, SPECIALIST_MODES, TERMINAL_REASONS
from milcah.manifest import build_manifest


def _coherence_capability():
    return next(c for c in build_manifest().capabilities if c.name == "coherence_check")


def test_manifest_conforms_and_is_built_from_the_contract():
    m = build_manifest()
    assert validate_manifest(m) == []
    assert m.product == "milcah"
    cc = _coherence_capability()
    # schema enum is sourced from the live contract, not duplicated
    assert set(cc.input_schema["properties"]["mode"]["enum"]) == set(SPECIALIST_MODES)
    assert cc.input_schema["required"] == list(REQUEST_FIELDS)


def test_manifest_describes_full_specialist_request_and_result():
    cc = _coherence_capability()
    props = cc.input_schema["properties"]
    assert {"query", "mode", "context", "max_iterations", "trace_id", "session_id"} <= set(props)
    assert props["mode"]["default"] == "coherence"
    assert props["max_iterations"]["minimum"] == 0

    out = cc.output_schema["properties"]
    for field in ("claims", "objections", "evidence", "citations"):
        assert out[field] == {"type": "array", "items": {"type": "string"}}
    assert out["confidence"]["minimum"] == 0 and out["confidence"]["maximum"] == 1
    assert set(out["terminal_reason"]["enum"]) == set(TERMINAL_REASONS)


def test_manifest_exposes_an_mcp_tool():
    assert "coherence_check" in [t["name"] for t in build_manifest().to_mcp()["tools"]]
