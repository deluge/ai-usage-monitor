import pytest
from freezegun import freeze_time


USAGE = {
    "five_hour": {"utilization": 42.0, "resets_at": "2026-11-24T14:30:00+00:00"},
    "seven_day": {"utilization": 87.5, "resets_at": "2026-11-27T09:00:00+00:00"},
}


@pytest.fixture
def display_module(micropython_modules):
    from display_usage.esp32 import display

    return display


@pytest.fixture
def oled(display_module):
    oled = display_module.Oled_m154_7p()
    oled.device.shown = 0  # ignore the clear screen of the init sequence
    return oled


def pixels_in(oled, left, top, right, bottom):
    return {(x, y) for x, y in oled.device.pixels if left <= x <= right and top <= y <= bottom}


def test_init(oled):
    from machine import Pin

    device = oled.device
    assert (device.width, device.height) == (128, 64)
    assert (device.spi.bus, device.spi.baudrate) == (1, 8_000_000)
    assert (device.spi.sck, device.spi.mosi) == (Pin(6), Pin(7))
    assert (device.dc, device.res, device.cs) == (Pin(5), Pin(4), Pin(10))
    assert device.settings == {"contrast": 200, "rotate": False}
    assert oled.timezone.utc_offset is None


def test_init_sends_ssd1309_sequence(display_module):
    device = display_module.Oled_m154_7p().device

    assert device.commands == list(display_module.SSD1309_INIT)
    assert 0xAD not in device.commands  # SSD1306 IREF command causes streaks on an SSD1309
    assert device.pixels == set()
    assert device.shown == 1


def test_init_with_options(display_module):
    from display_usage.utils import Timezone

    timezone = Timezone(1, dst="eu")
    oled = display_module.Oled_m154_7p(timezone=timezone, contrast=50, flip=True)

    assert oled.timezone is timezone
    assert oled.device.settings == {"contrast": 50, "rotate": True}


def test_fonts(oled):
    assert oled.textlength("Current", oled.font) > oled.textlength("Current", oled.font_small)


def test_clear_and_show(oled):
    oled.rectangle(0, 0, 9, 9, fill=True)

    oled.clear()
    oled.show()

    assert oled.device.pixels == set()
    assert oled.device.shown == 1


def test_rectangle(oled):
    oled.rectangle(10, 10, 19, 14)
    oled.rectangle(30, 10, 39, 14, fill=True)

    assert len(pixels_in(oled, 10, 10, 19, 14)) == 2 * 10 + 2 * 3  # outline only
    assert len(pixels_in(oled, 30, 10, 39, 14)) == 10 * 5


def test_text(oled):
    oled.text(0, 0, "Hi", oled.font)

    assert oled.device.pixels
    assert max(x for x, _ in oled.device.pixels) < oled.textlength("Hi", oled.font)


def test_show_message(oled):
    oled.show_message("First", "", "Third")

    assert pixels_in(oled, 0, 0, 127, 13)
    assert not pixels_in(oled, 0, 14, 127, 27)
    assert pixels_in(oled, 0, 28, 127, 41)
    assert oled.device.shown == 1


@freeze_time("2026-11-24 12:00:00")
def test_show_usage(oled):
    oled.show_usage(USAGE)

    assert len(pixels_in(oled, 0, 31, 127, 31)) == 128
    assert pixels_in(oled, 0, 0, 127, 30)
    assert pixels_in(oled, 0, 32, 127, 63)
    assert oled.device.shown == 1
