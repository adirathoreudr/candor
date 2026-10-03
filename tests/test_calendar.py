from datetime import date

import pytest

from candor.calendar import occurs_between, occurs_on


def ev(start, end, recurrence=None, all_day=False):
    return {"start": start, "end": end, "recurrence": recurrence, "all_day": all_day}


def test_single_event_on_its_day_only():
    e = ev("2026-09-23T09:00:00-07:00", "2026-09-23T12:00:00-07:00")
    assert occurs_on(e, date(2026, 9, 23))
    assert not occurs_on(e, date(2026, 9, 22)) and not occurs_on(e, date(2026, 9, 24))


def test_all_day_end_is_exclusive():
    e = ev("2026-09-24", "2026-09-26", all_day=True)
    assert occurs_on(e, date(2026, 9, 24)) and occurs_on(e, date(2026, 9, 25))
    assert not occurs_on(e, date(2026, 9, 26))


def test_weekly_weekdays_with_exception():
    e = ev("2026-09-11T08:00:00-07:00", "2026-09-11T10:00:00-07:00",
           ["RRULE:FREQ=WEEKLY;BYDAY=FR", "EXDATE;TZID=America/Los_Angeles:20260925T080000"])
    assert occurs_on(e, date(2026, 9, 18))
    assert not occurs_on(e, date(2026, 9, 25))          # exception
    assert not occurs_on(e, date(2026, 9, 17))          # Thursday
    assert not occurs_on(e, date(2026, 9, 4))           # before the series starts


def test_every_other_week():
    e = ev("2026-09-14T16:00:00-07:00", "2026-09-14T16:30:00-07:00", ["RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO"])
    assert occurs_on(e, date(2026, 9, 14)) and occurs_on(e, date(2026, 9, 28))
    assert not occurs_on(e, date(2026, 9, 21))


def test_until_and_count():
    daily_until = ev("2026-09-01T09:00:00-07:00", "2026-09-01T09:15:00-07:00", ["RRULE:FREQ=DAILY;UNTIL=20260903T235959Z"])
    assert occurs_on(daily_until, date(2026, 9, 3)) and not occurs_on(daily_until, date(2026, 9, 4))
    weekly_count = ev("2026-09-07T10:00:00-07:00", "2026-09-07T11:00:00-07:00", ["RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=2"])
    assert occurs_on(weekly_count, date(2026, 9, 14)) and not occurs_on(weekly_count, date(2026, 9, 21))


def test_unsupported_rule_fails_loud():
    with pytest.raises(ValueError):
        occurs_on(ev("2026-09-01T09:00:00-07:00", "2026-09-01T10:00:00-07:00", ["RDATE:20260905"]), date(2026, 9, 5))


def test_occurs_between_and_every_event_in_data_parses(corpus):
    for u in corpus.units:
        if u.source == "calendar":
            occurs_between(u.meta, date(2026, 9, 1), date(2026, 10, 31))   # raises on anything unsupported
    standup = next(u for u in corpus.units if u.meta.get("recurrence") and "MO,TU,WE,TH,FR" in u.meta["recurrence"][0])
    assert occurs_between(standup.meta, date(2026, 9, 19), date(2026, 9, 21))      # Sat-Mon includes Monday
    assert not occurs_between(standup.meta, date(2026, 9, 19), date(2026, 9, 20))  # weekend only
