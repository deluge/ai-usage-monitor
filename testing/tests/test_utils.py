import datetime
import io
import urllib.error

from freezegun import freeze_time
from PIL import ImageFont

from display_usage import utils
from display_usage.utils import (
    format_reset_current,
    format_reset_weekly,
    load_font,
    log,
    parse_reset,
    read_error_body,
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
