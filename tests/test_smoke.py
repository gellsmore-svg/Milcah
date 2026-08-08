import json
from pathlib import Path

import milcah
from milcah.cli import main
from milcah.contract import SpecialistResult


def test_version_is_set() -> None:
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        import tomli as tomllib  # type: ignore
    import pytest

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    declared = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    if milcah.__version__ != declared:
        pytest.skip(
            f"editable install is {milcah.__version__!r} but pyproject is "
            f"{declared!r} — run: pip install -e . --no-deps"
        )
    assert milcah.__version__ == declared


def test_cli_runs(capsys) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "Coherence Engine" in out


def test_specialist_cli_emits_contract_json(monkeypatch, capsys) -> None:
    captured = {}

    def fake_run_specialist(request, *, config):
        captured["request"] = request
        captured["model"] = config.orchestration.default_model
        return SpecialistResult(
            claims=["claim"],
            objections=["objection"],
            evidence=["evidence"],
            citations=["https://example.test"],
            confidence=0.42,
            trace_metadata={"mode": request.mode},
        )

    monkeypatch.setattr("milcah.specialist.run_specialist", fake_run_specialist)

    assert main([
        "specialist",
        "Is this coherent?",
        "--mode",
        "research",
        "--context",
        "Framework text.",
        "--model",
        "gemma",
        "--json",
    ]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["claims"] == ["claim"]
    assert payload["terminal_reason"] == "converged"
    assert captured["request"].mode == "research"
    assert captured["request"].context == "Framework text."
    assert captured["model"] == "gemma"


def test_specialist_cli_reads_context_file(monkeypatch, tmp_path, capsys) -> None:
    context_file = tmp_path / "framework.md"
    context_file.write_text("File context.", encoding="utf-8")
    captured = {}

    def fake_run_specialist(request, *, config):
        captured["context"] = request.context
        return SpecialistResult(terminal_reason="blocked", trace_metadata={"validation_errors": ["x"]})

    monkeypatch.setattr("milcah.specialist.run_specialist", fake_run_specialist)

    assert main(["specialist", "q", "--context-file", str(context_file)]) == 0
    out = capsys.readouterr().out
    assert "terminal_reason: blocked" in out
    assert captured["context"] == "File context."
