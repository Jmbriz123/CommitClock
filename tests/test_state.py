import multiprocessing
from datetime import UTC, datetime
from pathlib import Path
from threading import Event

import pytest

from commitclock.state import ActionKey, BusyError, StateError, StateStore, Status

KEY = ActionKey("workspace", "channel", datetime(2026, 10, 2, 9, tzinfo=UTC), "opening")


def test_persistence_duplicate_guards_and_attempt_ownership(tmp_path):
    with StateStore(tmp_path) as state:
        with pytest.raises(StateError, match="lock required"):
            state.claim(KEY, "opening")
        with state.submission_lock():
            attempt = state.claim(KEY, "opening")
            with pytest.raises(StateError, match="no longer owns"):
                state.finish(KEY, "stale-attempt", Status.CONFIRMED)
            state.finish(KEY, attempt, Status.CONFIRMED)
    with StateStore(tmp_path) as state:
        assert state.status(KEY) == Status.CONFIRMED
        with state.submission_lock(), pytest.raises(StateError, match="confirmed"):
            state.claim(KEY, "opening")
        assert len(state.attempts()) == 1
        assert state.attempts()[0]["outcome"] == "confirmed"
    assert (tmp_path / "state.sqlite3").stat().st_mode & 0o777 == 0o600


def test_recovery_does_not_touch_live_sender(tmp_path):
    with StateStore(tmp_path) as sender, StateStore(tmp_path) as reader:
        with sender.submission_lock():
            sender.claim(KEY, "opening")
            assert reader.status(KEY) == Status.IN_FLIGHT
            with pytest.raises(BusyError), reader.submission_lock():
                reader.recover_interrupted()
            assert sender.status(KEY) == Status.IN_FLIGHT
        with reader.submission_lock():
            assert reader.recover_interrupted() == 1
            assert reader.status(KEY) == Status.UNKNOWN
            with pytest.raises(StateError, match="unknown"):
                reader.claim(KEY, "opening")


def _crashing_sender(path, started):
    with StateStore(Path(path)) as state, state.submission_lock():
        state.claim(KEY, "opening")
        started.set()
        Event().wait(10)


def test_process_death_recovers_as_unknown(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    started = ctx.Event()
    process = ctx.Process(target=_crashing_sender, args=(str(tmp_path), started))
    process.start()
    try:
        assert started.wait(5)
        with StateStore(tmp_path) as state:
            with pytest.raises(BusyError), state.submission_lock():
                state.claim(KEY, "opening")
        process.terminate()
        process.join(5)
        with StateStore(tmp_path) as state, state.submission_lock():
            assert state.recover_interrupted() == 1
            assert state.status(KEY) == Status.UNKNOWN
            assert state.attempts()[0]["outcome"] == "unknown"
    finally:
        if process.is_alive():
            process.terminate()
        process.join(5)


def test_failed_retry_and_missed_require_explicit_opt_in(tmp_path):
    with StateStore(tmp_path) as state, state.submission_lock():
        state.ensure(KEY, Status.MISSED)
        with pytest.raises(StateError, match="missed"):
            state.claim(KEY, "opening")
        attempt = state.claim(KEY, "opening", allow_missed=True)
        state.finish(KEY, attempt, Status.FAILED)
        retry = state.claim(KEY, "opening")
        assert retry != attempt
        state.finish(KEY, retry, Status.UNKNOWN)
        with pytest.raises(StateError, match="unknown"):
            state.claim(KEY, "opening")
