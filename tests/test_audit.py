import json
from datetime import UTC, datetime

from commitclock.audit import audit_snapshot
from commitclock.cli import main
from commitclock.privacy import redact
from commitclock.state import ActionKey, StateStore, Status


def test_redaction_covers_credentials_and_terminal_controls():
    text = (
        'api_key="sensitive value"\npassword=hidden\nAuthorization: Bearer token-value\n'
        "-----BEGIN PRIVATE KEY-----\nprivate-material\n-----END PRIVATE KEY-----\n"
        "literal-known-secret\x1b[31m"
    )
    result = redact(text, ["literal-known-secret"])
    for secret in (
        "sensitive value",
        "hidden",
        "token-value",
        "private-material",
        "literal-known-secret",
        "\x1b",
    ):
        assert secret not in result
    assert "[REDACTED]" in result


def test_audit_reports_attempt_outcome_without_secret(tmp_path):
    key = ActionKey("https://workspace", "private-channel", datetime.now(UTC), "eod")
    with StateStore(tmp_path) as state, state.submission_lock():
        attempt = state.claim(key, "eod")
        state.finish(key, attempt, Status.UNKNOWN)
        snapshot = audit_snapshot(state, ["private-channel"])
    assert "private-channel" not in json.dumps(snapshot)
    assert snapshot["attempts"][0]["outcome"] == "unknown"
    assert snapshot["attempts"][0]["payload_type"] == "eod"
    assert snapshot["attempts"][0]["finished_at"]


def test_status_command_reads_local_journal(tmp_path, capsys):
    assert main(["--state-dir", str(tmp_path), "status"]) == 0
    assert json.loads(capsys.readouterr().out) == {"actions": [], "attempts": []}
