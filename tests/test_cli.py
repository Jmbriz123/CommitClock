import pytest

from commitclock.cli import main


def test_help_needs_no_credentials(monkeypatch, capsys):
    monkeypatch.delenv("MATTERMOST_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(SystemExit) as result:
        main(["--help"])
    assert result.value.code == 0
    assert "commitclock" in capsys.readouterr().out
