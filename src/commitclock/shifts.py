"""Dated wall-clock schedules with UTC identities and comparison boundaries."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from commitclock.config import Config


class ScheduleError(ValueError):
    """A dated schedule cannot be resolved safely."""


class Action(StrEnum):
    CLKIN = "clkin"
    OPENING = "opening"
    PROGRESS = "progress"
    EOD = "eod"
    CLKOUT = "clkout"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ScheduleError("Schedule timestamps must include a timezone")
    return value.astimezone(UTC)


@dataclass(frozen=True)
class ShiftWindow:
    start: datetime = field(compare=False)
    end: datetime = field(compare=False)
    start_utc: datetime = field(init=False, repr=False)
    end_utc: datetime = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_utc", _utc(self.start))
        object.__setattr__(self, "end_utc", _utc(self.end))
        if self.end_utc <= self.start_utc:
            raise ScheduleError("Shift end must follow its start")

    @property
    def start_date(self) -> date:
        return self.start.date()

    @property
    def identity(self) -> str:
        """Canonical instant used alongside workspace, channel and action keys."""
        return self.start_utc.isoformat()


@dataclass(frozen=True)
class ScheduledAction:
    action: Action
    due_at: datetime = field(compare=False)
    shift: ShiftWindow
    due_at_utc: datetime = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "due_at_utc", _utc(self.due_at))
        if not self.shift.start_utc <= self.due_at_utc <= self.shift.end_utc:
            raise ScheduleError("Scheduled action must fall within its shift")


def _local_datetime(day: date, wall_time: time, zone: ZoneInfo) -> datetime:
    if wall_time.tzinfo is not None:
        raise ScheduleError("Schedule times must be local wall-clock times")
    naive = datetime.combine(day, wall_time)
    candidate = naive.replace(tzinfo=zone, fold=0)
    round_trip = candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None)
    if round_trip != naive:
        raise ScheduleError(
            f"Scheduled time {naive.isoformat()} does not exist in {zone.key}; "
            "adjust the schedule for this date"
        )
    return candidate


def shift_for_date(start_date: date, config: Config) -> ShiftWindow:
    """Build a shift anchored to its local start date, including overnight actions."""
    zone = ZoneInfo(config.timezone)
    end_date = start_date + timedelta(days=config.end <= config.start)
    shift = ShiftWindow(
        start=_local_datetime(start_date, config.start, zone),
        end=_local_datetime(end_date, config.end, zone),
    )
    # Validate intermediate times too: an endpoint can exist while a check-in falls
    # in a spring-forward gap. Do not silently move an attendance event.
    scheduled_actions(shift, config)
    return shift


def latest_shift(now: datetime, config: Config) -> ShiftWindow:
    """Select the most recently started shift, even between consecutive shifts.

    This deliberately includes a completed overnight shift at midnight and until
    the next start. It does not select an upcoming shift or imply one is active.
    """
    current_utc = _utc(now)
    zone = ZoneInfo(config.timezone)
    today = now.astimezone(zone).date()
    start_today = _local_datetime(today, config.start, zone)
    start_date = today if _utc(start_today) <= current_utc else today - timedelta(days=1)
    return shift_for_date(start_date, config)


def scheduled_actions(shift: ShiftWindow, config: Config) -> tuple[ScheduledAction, ...]:
    """Return ordered events; clock-in always precedes simultaneous opening."""
    zone = ZoneInfo(config.timezone)
    start_date = shift.start.astimezone(zone).date()

    def at(wall_time: time) -> datetime:
        day = start_date + timedelta(days=wall_time < config.start)
        return _local_datetime(day, wall_time, zone)

    events = (
        ScheduledAction(Action.CLKIN, shift.start, shift),
        ScheduledAction(Action.OPENING, shift.start, shift),
        ScheduledAction(Action.PROGRESS, at(config.progress), shift),
        ScheduledAction(Action.EOD, at(config.eod), shift),
        ScheduledAction(Action.CLKOUT, shift.end, shift),
    )
    instants = [event.due_at_utc for event in events]
    if not instants[0] == instants[1] < instants[2] < instants[3] < instants[4]:
        raise ScheduleError("Dated schedule must order start, progress, eod, end")
    return events


def evidence_end(shift: ShiftWindow, now: datetime) -> datetime:
    """Return the UTC exclusive upper bound, clamped to an empty/full shift."""
    return max(shift.start_utc, min(_utc(now), shift.end_utc))
