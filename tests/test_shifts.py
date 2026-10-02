from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from commitclock.config import Config
from commitclock.shifts import (
    Action,
    ScheduledAction,
    ScheduleError,
    ShiftWindow,
    evidence_end,
    latest_shift,
    scheduled_actions,
    shift_for_date,
)


@pytest.fixture
def config(tmp_path):
    return Config(repository=Path.cwd(), state_dir=tmp_path)


@pytest.mark.parametrize(
    ("timestamp", "expected_date"),
    [
        ("2026-10-02T16:59:00+08:00", date(2026, 10, 1)),
        ("2026-10-02T17:00:00+08:00", date(2026, 10, 2)),
        ("2026-10-02T23:59:00+08:00", date(2026, 10, 2)),
        ("2026-10-03T00:00:00+08:00", date(2026, 10, 2)),
        ("2026-10-03T01:00:00+08:00", date(2026, 10, 2)),
        ("2026-10-03T16:59:00+08:00", date(2026, 10, 2)),
        ("2026-10-03T17:00:00+08:00", date(2026, 10, 3)),
    ],
)
def test_latest_shift_preserves_overnight_anchor(config, timestamp, expected_date):
    assert latest_shift(datetime.fromisoformat(timestamp), config).start_date == expected_date


def test_default_events_and_utc_identity(config):
    shift = shift_for_date(date(2026, 10, 2), config)
    events = scheduled_actions(shift, config)
    assert [event.action for event in events] == list(Action)
    assert [event.due_at.strftime("%Y-%m-%d %H:%M") for event in events] == [
        "2026-10-02 17:00",
        "2026-10-02 17:00",
        "2026-10-02 20:30",
        "2026-10-02 23:30",
        "2026-10-03 00:00",
    ]
    assert shift.identity == "2026-10-02T09:00:00+00:00"
    assert events[-1].shift is shift
    assert shift == ShiftWindow(shift.start_utc, shift.end_utc)
    assert hash(shift) == hash(ShiftWindow(shift.start_utc, shift.end_utc))
    with pytest.raises(FrozenInstanceError):
        shift.start = shift.end


@pytest.mark.parametrize(
    ("times", "event_dates"),
    [
        ((9, 12, 16, 17), [2, 2, 2, 2, 2]),
        ((22, 1, 5, 6), [2, 2, 3, 3, 3]),
    ],
)
def test_custom_day_and_night_schedules(config, times, event_dates):
    start, progress, eod, end = map(time, times)
    config = replace(config, start=start, progress=progress, eod=eod, end=end)
    shift = shift_for_date(date(2026, 10, 2), config)
    assert [event.due_at.day for event in scheduled_actions(shift, config)] == event_dates


def test_evidence_excludes_future_and_caps_at_end(config):
    shift = shift_for_date(date(2026, 10, 2), config)
    assert evidence_end(shift, shift.start - timedelta(minutes=1)) == shift.start_utc
    assert evidence_end(shift, shift.start) == shift.start_utc
    during = shift.start + timedelta(hours=2)
    assert evidence_end(shift, during) == during.astimezone(UTC)
    assert evidence_end(shift, shift.end) == shift.end_utc
    assert evidence_end(shift, shift.end + timedelta(hours=3)) == shift.end_utc


@pytest.mark.parametrize("day, hours", [(date(2026, 3, 8), 3), (date(2026, 11, 1), 5)])
def test_dst_changes_elapsed_duration_without_changing_wall_times(config, day, hours):
    config = replace(
        config,
        timezone="America/New_York",
        start=time(0),
        progress=time(1),
        eod=time(3),
        end=time(4),
    )
    shift = shift_for_date(day, config)
    assert shift.end_utc - shift.start_utc == timedelta(hours=hours)
    assert [e.due_at.hour for e in scheduled_actions(shift, config)] == [0, 0, 1, 3, 4]


def test_nonexistent_dst_checkin_is_rejected(config):
    config = replace(
        config,
        timezone="America/New_York",
        start=time(0),
        progress=time(2, 30),
        eod=time(3),
        end=time(4),
    )
    with pytest.raises(ScheduleError, match="2026-03-08T02:30:00 does not exist"):
        shift_for_date(date(2026, 3, 8), config)


def test_repeated_dst_time_uses_first_occurrence_and_utc_comparisons(config):
    zone = ZoneInfo("America/New_York")
    config = replace(
        config,
        timezone=zone.key,
        start=time(1, 30),
        progress=time(2),
        eod=time(3),
        end=time(4),
    )
    # Second 01:15 follows first 01:30 in UTC despite its earlier wall time.
    now = datetime(2026, 11, 1, 1, 15, tzinfo=zone, fold=1)
    shift = latest_shift(now, config)
    assert shift.start_date == date(2026, 11, 1)
    assert shift.start.fold == 0
    assert shift.start_utc == datetime(2026, 11, 1, 5, 30, tzinfo=UTC)
    assert evidence_end(shift, now) == datetime(2026, 11, 1, 6, 15, tzinfo=UTC)
    second_start = shift.start.replace(fold=1)
    assert shift != ShiftWindow(second_start, shift.end)


def test_utc_input_selects_local_shift(config):
    assert latest_shift(datetime(2026, 10, 2, 16, tzinfo=UTC), config).start_date == date(
        2026, 10, 2
    )


def test_naive_instants_and_invalid_windows_are_rejected(config):
    shift = shift_for_date(date(2026, 10, 2), config)
    with pytest.raises(ScheduleError, match="timezone"):
        latest_shift(datetime(2026, 10, 2), config)
    with pytest.raises(ScheduleError, match="timezone"):
        evidence_end(shift, datetime(2026, 10, 2))
    with pytest.raises(ScheduleError, match="follow"):
        ShiftWindow(shift.end, shift.start)
    with pytest.raises(ScheduleError, match="within"):
        ScheduledAction(Action.CLKOUT, shift.end + timedelta(seconds=1), shift)
    with pytest.raises(ScheduleError, match="order"):
        shift_for_date(date(2026, 10, 2), replace(config, progress=time(23, 45)))
