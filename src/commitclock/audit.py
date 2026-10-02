"""Structured, sanitized views of the action journal; no raw provider responses."""

import json
from collections.abc import Iterable

from commitclock.privacy import redact
from commitclock.state import StateStore


def audit_snapshot(state: StateStore, secrets: Iterable[str] = ()) -> dict:
    def clean(value):
        if isinstance(value, str):
            return redact(value, secrets)
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    def expand(record, key):
        workspace, channel, shift_start, action = json.loads(record.pop(key))
        return {
            **record,
            "workspace": workspace,
            "channel": channel,
            "shift_start": shift_start,
            "action": action,
        }

    return clean(
        {
            "actions": [expand(row, "key") for row in state.actions()],
            "attempts": [expand(row, "action_key") for row in state.attempts()],
        }
    )
