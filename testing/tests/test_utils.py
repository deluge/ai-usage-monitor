import calendar

import pytest
from freezegun import freeze_time

from conftest import NOW
from display_usage import utils
from display_usage.utils import (
    Timezone,
    format_reset_current,
    format_reset_weekly,
    log,
    parse_reset,
    sunday_of_month,
    unix_time,
)


def utc(year, month, day, hour, minute, second):
    return calendar.timegm((year, month, day, hour, minute, second, 0, 0, 0))


def test_log(capsys):
    log("Hello")

    assert capsys.readouterr().err == "Hello\n"


@freeze_time("2026-11-24 12:00:00")
def test_unix_time():
    assert unix_time() == NOW


@freeze_time("2026-11-24 12:00:00")
def test_unix_time_with_2000_epoch(monkeypatch):
    """Some MicroPython ports count from 2000."""
    monkeypatch.setattr(utils, "EPOCH_OFFSET", 946_684_800)
    monkeypatch.setattr(utils.time, "time", lambda: NOW - 946_684_800)

    assert unix_time() == NOW


class TestParseReset:
    @pytest.mark.parametrize("value", [None, ""])
    def test_empty(self, value):
        assert parse_reset(value) is None

    @pytest.mark.parametrize(
        "value",
        [
            "2026-11-24T17:30:00+00:00",
            "2026-11-24T17:30:00.123456+00:00",
            "2026-11-24T17:30:00Z",
            "2026-11-24T17:30:00",
            "2026-11-24T19:00:00+01:30",
            "2026-11-24T12:30:00.5-05:00",
        ],
    )
    def test_timestamp(self, value):
        assert parse_reset(value) == utc(2026, 11, 24, 17, 30, 0)


@pytest.mark.parametrize(
    "year, month, week, day",
    [
        (2026, 3, -1, 29),
        (2026, 10, -1, 25),
        (2026, 3, 2, 8),
        (2026, 11, 1, 1),
        (2026, 2, 1, 1),  # the 1st is a Sunday
        (2026, 12, -1, 27),  # last Sunday of the year (wraps into next January)
        (2027, 3, -1, 28),
    ],
)
def test_sunday_of_month(year, month, week, day):
    assert sunday_of_month(year, month, week) == day


class TestTimezone:
    def test_invalid_dst(self):
        with pytest.raises(ValueError):
            Timezone(1, dst="asia")

    def test_system_timezone(self):
        assert Timezone().localtime(NOW)[:6] == (2026, 11, 24, 12, 0, 0)

    def test_fixed_offset(self):
        timezone = Timezone(5.5)

        assert timezone.localtime(NOW)[:6] == (2026, 11, 24, 17, 30, 0)
        assert timezone.offset(utc(2026, 7, 1, 12, 0, 0)) == 5.5 * 3600

    @pytest.mark.parametrize(
        "moment, offset",
        [
            (utc(2026, 3, 29, 0, 59, 59), 3600),
            (utc(2026, 3, 29, 1, 0, 0), 7200),
            (utc(2026, 7, 1, 12, 0, 0), 7200),
            (utc(2026, 10, 25, 0, 59, 59), 7200),
            (utc(2026, 10, 25, 1, 0, 0), 3600),
        ],
    )
    def test_eu_summer_time(self, moment, offset):
        assert Timezone(1, dst="eu").offset(moment) == offset

    @pytest.mark.parametrize(
        "moment, offset",
        [
            (utc(2026, 3, 8, 6, 59, 59), -5 * 3600),  # 01:59:59 EST
            (utc(2026, 3, 8, 7, 0, 0), -4 * 3600),  # 02:00 EST becomes 03:00 EDT
            (utc(2026, 11, 1, 5, 59, 59), -4 * 3600),  # 01:59:59 EDT
            (utc(2026, 11, 1, 6, 0, 0), -5 * 3600),  # 02:00 EDT becomes 01:00 EST
        ],
    )
    def test_us_summer_time(self, moment, offset):
        assert Timezone(-5, dst="us").offset(moment) == offset

    def test_localtime_with_summer_time(self):
        local = Timezone(1, dst="eu").localtime(utc(2026, 7, 1, 12, 0, 0))

        assert local[:6] == (2026, 7, 1, 14, 0, 0)


@freeze_time("2026-11-24 12:00:00")
class TestFormatResetCurrent:
    def test_unknown(self):
        assert format_reset_current(None, Timezone()) == "Reset: --"

    def test_remaining_time(self):
        reset_at = utc(2026, 11, 24, 14, 5, 30)

        assert format_reset_current(reset_at, Timezone()) == "Reset 14:05 (2h05)"
        assert format_reset_current(reset_at, Timezone(1)) == "Reset 15:05 (2h05)"

    def test_reset_in_the_past(self):
        reset_at = utc(2026, 11, 24, 11, 0, 0)

        assert format_reset_current(reset_at, Timezone()) == "Reset 11:00 (0h00)"


class TestFormatResetWeekly:
    def test_unknown(self):
        assert format_reset_weekly(None, Timezone()) == "Reset: --"

    def test_date(self):
        reset_at = utc(2026, 11, 27, 9, 5, 0)

        assert format_reset_weekly(reset_at, Timezone()) == "Reset Fri 27.11. 09:05"

    def test_date_changes_with_timezone(self):
        reset_at = utc(2026, 11, 27, 23, 30, 0)

        assert format_reset_weekly(reset_at, Timezone(1)) == "Reset Sat 28.11. 00:30"
