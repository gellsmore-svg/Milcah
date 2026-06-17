import milcah
from milcah.cli import main


def test_version_is_set() -> None:
    assert milcah.__version__ == "0.2.0"


def test_cli_runs(capsys) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "Coherence Engine" in out
