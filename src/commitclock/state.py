"""Private local action journal with transactional claims and process-safe recovery."""

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4


class StateError(RuntimeError):
    """An invalid or unsafe action-state transition."""


class BusyError(StateError):
    """Another local process currently owns submission/recovery."""


class Status(StrEnum):
    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    MISSED = "missed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ActionKey:
    workspace: str
    channel: str
    shift_start: datetime
    action: str

    @property
    def identifier(self) -> str:
        if self.shift_start.tzinfo is None:
            raise StateError("Action identity requires a timezone-aware shift start")
        if self.action not in {"clkin", "opening", "progress", "eod", "clkout"}:
            raise StateError("Unsupported action")
        return json.dumps(
            [
                self.workspace,
                self.channel,
                self.shift_start.astimezone(UTC).isoformat(),
                self.action,
            ]
        )


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


class StateStore:
    """Own one connection. Use submission_lock across claim, delivery, and finish.

    The lock is Linux/POSIX advisory locking; every sender must cooperate. Recovery
    uses the same stable lock file and never infers death from a PID or heartbeat.
    """

    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory.chmod(0o700)
        path = directory / "state.sqlite3"
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.fchmod(descriptor, 0o600)
        os.close(descriptor)
        self.db = sqlite3.connect(path, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS actions (
                key TEXT PRIMARY KEY,
                status TEXT NOT NULL CHECK(status IN
                    ('pending','in_flight','confirmed','failed','missed','unknown')),
                attempt_id TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS attempts (
                id TEXT PRIMARY KEY,
                action_key TEXT NOT NULL REFERENCES actions(key),
                started_at TEXT NOT NULL,
                finished_at TEXT,
                outcome TEXT NOT NULL,
                payload_type TEXT NOT NULL
            );
        """)
        self._locked = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.db.close()

    @contextmanager
    def submission_lock(self) -> Iterator[None]:
        import fcntl

        if self._locked:
            raise StateError("Submission lock is not reentrant")
        fd = os.open(
            self.directory / "submission.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise BusyError("Another CommitClock submission or recovery is active") from None
            self._locked = True
            try:
                yield
            finally:
                self._locked = False
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def _require_lock(self):
        if not self._locked:
            raise StateError("Submission lock required")

    def ensure(self, key: ActionKey, status: Status = Status.PENDING) -> None:
        if status not in {Status.PENDING, Status.MISSED}:
            raise StateError("New actions must be pending or missed")
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO actions VALUES (?, ?, NULL, ?)",
                (key.identifier, status, _timestamp()),
            )

    def claim(self, key: ActionKey, payload_type: str, *, allow_missed: bool = False) -> str:
        self._require_lock()
        if payload_type not in {"command", "opening", "progress", "eod"}:
            raise StateError("Unsupported payload type")
        identifier = key.identifier
        attempt = str(uuid4())
        now = _timestamp()
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute(
                "INSERT OR IGNORE INTO actions VALUES (?, 'pending', NULL, ?)", (identifier, now)
            )
            status = self.db.execute(
                "SELECT status FROM actions WHERE key=?", (identifier,)
            ).fetchone()[0]
            allowed = {Status.PENDING, Status.FAILED}
            if allow_missed:
                allowed.add(Status.MISSED)
            if status not in allowed:
                raise StateError(f"Action is {status}; submission refused")
            self.db.execute(
                "UPDATE actions SET status='in_flight', attempt_id=?, updated_at=? WHERE key=?",
                (attempt, now, identifier),
            )
            self.db.execute(
                "INSERT INTO attempts VALUES (?, ?, ?, NULL, 'in_flight', ?)",
                (attempt, identifier, now, payload_type),
            )
        return attempt

    def finish(self, key: ActionKey, attempt: str, outcome: Status) -> None:
        self._require_lock()
        if outcome not in {Status.CONFIRMED, Status.FAILED, Status.UNKNOWN}:
            raise StateError("Submission requires a terminal outcome")
        now = _timestamp()
        with self.db:
            count = self.db.execute(
                "UPDATE actions SET status=?, updated_at=? "
                "WHERE key=? AND status='in_flight' AND attempt_id=?",
                (outcome, now, key.identifier, attempt),
            ).rowcount
            if count != 1:
                raise StateError("Attempt no longer owns this action")
            self.db.execute(
                "UPDATE attempts SET outcome=?, finished_at=? WHERE id=?", (outcome, now, attempt)
            )

    def recover_interrupted(self) -> int:
        """Only call under the process lock; an active sender makes recovery busy."""
        self._require_lock()
        now = _timestamp()
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute(
                "UPDATE attempts SET outcome='unknown', finished_at=? WHERE outcome='in_flight'",
                (now,),
            )
            count = self.db.execute(
                "UPDATE actions SET status='unknown', updated_at=? WHERE status='in_flight'", (now,)
            ).rowcount
        return count

    def status(self, key: ActionKey) -> Status | None:
        row = self.db.execute(
            "SELECT status FROM actions WHERE key=?", (key.identifier,)
        ).fetchone()
        return Status(row[0]) if row else None

    def actions(self) -> list[dict]:
        return [
            dict(row) for row in self.db.execute("SELECT * FROM actions ORDER BY updated_at, key")
        ]

    def attempts(self) -> list[dict]:
        return [
            dict(row) for row in self.db.execute("SELECT * FROM attempts ORDER BY started_at, id")
        ]
