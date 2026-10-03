"""When a calendar event happens, including recurring ones, so "what's on my calendar on X" can be answered.

Supports the RFC 5545 subset the Calendar API emits for simple series: FREQ=DAILY/WEEKLY with BYDAY,
INTERVAL, UNTIL and COUNT, plus EXDATE. Anything else raises: a silently wrong calendar is worse
than a loud failure.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from candor import config

LOCAL = ZoneInfo(config.TIMEZONE)
_DAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def _parse(value: str) -> datetime | date:
    return date.fromisoformat(value) if len(value) == 10 else datetime.fromisoformat(value)


def _local_date(value: datetime | date) -> date:
    return value.astimezone(LOCAL).date() if isinstance(value, datetime) else value


def _rule(recurrence: list[str]) -> tuple[dict, set[date]]:
    rule, exdates = {}, set()
    for line in recurrence:
        if line.startswith("RRULE:"):
            rule = dict(part.split("=", 1) for part in line[len("RRULE:"):].split(";"))
        elif line.startswith("EXDATE"):
            for stamp in line.split(":", 1)[1].split(","):
                exdates.add(date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8])))
        else:
            raise ValueError(f"unsupported recurrence line: {line}")
    return rule, exdates


def _in_pattern(rule: dict, first: date, day: date) -> bool:
    """Whether `day` is in the series' pattern (frequency, weekdays, interval), ignoring COUNT/UNTIL/EXDATE."""
    freq, interval = rule.get("FREQ"), int(rule.get("INTERVAL", "1"))
    if freq == "DAILY":
        return (day - first).days % interval == 0
    if freq == "WEEKLY":
        weeks = (day - (first - timedelta(days=first.weekday()))).days // 7
        return _DAYS[day.weekday()] in rule.get("BYDAY", _DAYS[first.weekday()]).split(",") and weeks % interval == 0
    raise ValueError(f"unsupported recurrence frequency: {freq}")


def occurs_on(meta: dict, day: date) -> bool:
    """Whether the event (unit.meta of a calendar unit) takes place on `day`, in local time."""
    start, end = _parse(meta["start"]), _parse(meta["end"])
    first = _local_date(start)
    if not meta.get("recurrence"):
        last = _local_date(end) - timedelta(days=1) if meta.get("all_day") else _local_date(end)
        return first <= day <= max(first, last)
    rule, exdates = _rule(meta["recurrence"])
    if day < first or not _in_pattern(rule, first, day):
        return False
    if "UNTIL" in rule:
        u = rule["UNTIL"]
        if day > date(int(u[:4]), int(u[4:6]), int(u[6:8])):
            return False
    if "COUNT" in rule:   # COUNT counts series occurrences before EXDATE removes any (RFC 5545)
        nth = sum(_in_pattern(rule, first, first + timedelta(days=k)) for k in range((day - first).days + 1))
        if nth > int(rule["COUNT"]):
            return False
    return day not in exdates


def occurs_between(meta: dict, start: date, end: date) -> bool:
    """Whether the event takes place on any day in [start, end], inclusive."""
    return any(occurs_on(meta, start + timedelta(days=k)) for k in range((end - start).days + 1))
