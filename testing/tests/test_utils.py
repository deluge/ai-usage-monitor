import datetime
import io
import urllib.error

import pytest
from freezegun import freeze_time
from PIL import ImageFont

from display_usage import utils
from display_usage.utils import (
    format_reset_current,
    format_reset_weekly,
    format_updated_at,
    load_font,
    log,
    parse_reset,
    read_error_body,
    read_window,
)
from testing.fakes.api import http_error


def test_log(capsys):
    log("Hello")

    assert capsys.readouterr().err == "Hello\n"


class TestReadErrorBody:
    def test_body(self):
        assert read_error_body(http_error("https://x", 400, "bad request")) == "bad request"

    def test_limit(self):
        assert read_error_body(http_error("https://x", 400, "abcdef"), limit=3) == "abc"

    def test_undecodable_bytes_are_replaced(self):
        error = urllib.error.HTTPError("https://x", 400, "", None, io.BytesIO(b"\xffok"))

        assert read_error_body(error) == "�ok"

    def test_unreadable(self):
        error = http_error("https://x", 400)
        error.fp.close()

        assert read_error_body(error) == ""


class TestLoadFont:
    def test_truetype_font(self, monkeypatch, tmp_path):
        font_file = tmp_path / "DejaVuSans-Bold.ttf"
        font_file.touch()
        loaded = []
        monkeypatch.setattr(utils, "FONT_DIRECTORY", f"{tmp_path}/")
        monkeypatch.setattr(
            ImageFont, "truetype", lambda path, size: loaded.append((path, size))
        )

        load_font(11)

        assert loaded == [(str(font_file), 11)]

    def test_default_font(self, monkeypatch, tmp_path):
        monkeypatch.setattr(utils, "FONT_DIRECTORY", f"{tmp_path}/")

        assert isinstance(load_font(11), ImageFont.ImageFont | ImageFont.FreeTypeFont)


class TestParseReset:
    def test_empty(self):
        assert parse_reset(None) is None
        assert parse_reset("") is None

    def test_timestamp(self):
        reset_at = parse_reset("2026-11-24T17:30:00+00:00")

        assert reset_at.tzinfo is not None
        assert reset_at == datetime.datetime(2026, 11, 24, 17, 30, tzinfo=datetime.UTC)


class TestFormatResetCurrent:
    def test_unknown(self):
        assert format_reset_current(None) == "Reset: --"

    @freeze_time("2026-11-24 12:00:00")
    def test_remaining_time(self):
        reset_at = parse_reset("2026-11-24T14:05:30+00:00")

        assert format_reset_current(reset_at) == f"Reset {reset_at:%H:%M} (2h05)"

    @freeze_time("2026-11-24 12:00:00")
    def test_reset_in_the_past(self):
        reset_at = parse_reset("2026-11-24T11:00:00+00:00")

        assert format_reset_current(reset_at) == f"Reset {reset_at:%H:%M} (0h00)"


class TestFormatResetWeekly:
    def test_unknown(self):
        assert format_reset_weekly(None) == "Reset: --"

    def test_date(self):
        reset_at = datetime.datetime(2026, 11, 27, 9, 5)

        assert format_reset_weekly(reset_at) == "Reset Fri 27.11. 09:05"


def test_format_updated_at():
    updated_at = datetime.datetime(2026, 11, 24, 9, 5)

    assert format_updated_at(updated_at) == "Data from Tue 09:05"


@freeze_time("2026-11-24 12:00:00")
class TestReadWindow:
    def test_missing(self):
        assert read_window(None) == (None, None)
        assert read_window({}) == (None, None)

    def test_active(self):
        window = {"utilization": 42.0, "resets_at": "2026-11-24T14:30:00+00:00"}

        assert read_window(window) == (42.0, parse_reset("2026-11-24T14:30:00+00:00"))

    def test_without_reset_time(self):
        assert read_window({"utilization": 0.0, "resets_at": None}) == (0.0, None)

    @pytest.mark.parametrize("resets_at", ["2026-11-24T12:00:00+00:00", "2026-11-24T09:00:00Z"])
    def test_expired(self, resets_at):
        """The window has reset: its old utilization no longer applies."""
        assert read_window({"utilization": 87.0, "resets_at": resets_at}) == (0.0, None)
