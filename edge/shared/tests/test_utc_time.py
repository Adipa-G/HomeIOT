import calendar
import datetime

import pytest

from edge.shared.app.utc_time import (
    datetime_to_epoch,
    epoch_to_datetime,
    epoch_to_iso,
    iso_to_epoch,
)


@pytest.mark.parametrize(
    "value",
    [
        "1970-01-01T00:00:00Z",
        "2000-01-01T00:00:00Z",
        "2021-01-01T00:05:00Z",
        "2024-02-29T23:59:59Z",
        "2026-10-23T12:39:23Z",
        "2100-03-01T06:07:08Z",
    ],
)
def test_iso_to_epoch_matches_calendar_timegm(value):
    expected = calendar.timegm(datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").timetuple())

    assert iso_to_epoch(value) == expected
    assert epoch_to_iso(expected) == value


def test_epoch_to_iso_round_trips_every_day_across_leap_years():
    start = iso_to_epoch("2020-12-25T13:14:15Z")
    for day in range(0, 2000):
        seconds = start + day * 86400 + day * 37
        assert iso_to_epoch(epoch_to_iso(seconds)) == seconds


@pytest.mark.parametrize("value", [None, "", "2021-01-01", "garbage-value-here!", 12345])
def test_iso_to_epoch_rejects_malformed(value):
    assert iso_to_epoch(value) is None


def test_epoch_to_datetime_matches_gmtime_including_weekday():
    import time

    for seconds in (0, 951782400, 1609459200, 1792630800, 4102444800):
        expected = time.gmtime(seconds)
        assert epoch_to_datetime(seconds) == (
            expected.tm_year,
            expected.tm_mon,
            expected.tm_mday,
            expected.tm_hour,
            expected.tm_min,
            expected.tm_sec,
            expected.tm_wday,
        )


def test_datetime_to_epoch_round_trips():
    for seconds in (0, 1609459200, 1792630815):
        assert datetime_to_epoch(epoch_to_datetime(seconds)) == seconds
