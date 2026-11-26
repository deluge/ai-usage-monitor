import datetime

import pytest
from freezegun import freeze_time
from luma.core.device import dummy
from PIL import ImageChops

from display_usage import display as display_module
from display_usage.display import BaseDisplay, Oled_m154_7p


USAGE = {
    "five_hour": {"utilization": 42.0, "resets_at": "2026-11-24T14:30:00+00:00"},
    "seven_day": {"utilization": 87.5, "resets_at": "2026-11-27T09:00:00+00:00"},
}


@pytest.fixture
def created():
    return {}


@pytest.fixture
def fake_hardware(monkeypatch, created):
    """Replace SPI and the controller with luma's in-memory dummy device."""

    def fake_spi(**kwargs):
        created["spi"] = kwargs
        return "serial"

    def fake_controller(serial, width, height, rotate):
        created["controller"] = (serial, width, height, rotate)
        device = dummy(width=width, height=height, rotate=rotate, mode="1")
        device.contrast = lambda level: created.setdefault("contrast", level)
        return device

    monkeypatch.setattr(display_module, "spi", fake_spi)
    monkeypatch.setitem(display_module.CONTROLLERS, "ssd1309", fake_controller)


@pytest.fixture
def oled(fake_hardware):
    return Oled_m154_7p()


def lit_pixels(image, box=None):
    image = image.crop(box) if box else image
    return sum(image.convert("L").histogram()[1:])


def test_base_display_methods_must_be_implemented():
    with pytest.raises(NotImplementedError):
        BaseDisplay().show_message("x")
    with pytest.raises(NotImplementedError):
        BaseDisplay().show_usage(USAGE)


def test_init(oled, created):
    assert created["spi"] == {
        "port": 0,
        "device": 0,
        "gpio_DC": 24,
        "gpio_RST": 25,
        "bus_speed_hz": 8_000_000,
    }
    assert created["controller"] == ("serial", 128, 64, 0)
    assert created["contrast"] == 200


def test_unknown_controller(fake_hardware):
    with pytest.raises(KeyError):
        Oled_m154_7p(controller="unknown")


def test_show_loading(oled):
    oled.show_loading(1)
    one_dot = oled.device.image.copy()

    oled.show_loading()

    assert lit_pixels(oled.device.image) > lit_pixels(one_dot)


def test_show_message(oled):
    oled.show_message("First", "", "Third")

    image = oled.device.image
    assert lit_pixels(image, (0, 0, 128, 14)) > 0
    assert lit_pixels(image, (0, 14, 128, 28)) == 0
    assert lit_pixels(image, (0, 28, 128, 42)) > 0


@freeze_time("2026-11-24 12:00:00")
class TestShowUsage:
    def test_draws_both_blocks_and_divider(self, oled):
        oled.show_usage(USAGE)

        image = oled.device.image
        assert lit_pixels(image, (0, 31, 128, 32)) == 128
        assert lit_pixels(image, (0, 0, 128, 31)) > 0
        assert lit_pixels(image, (0, 32, 128, 64)) > 0

    def test_bar_grows_with_utilization(self, oled):
        oled.show_usage({"five_hour": {"utilization": 10}})
        low = lit_pixels(oled.device.image, (oled.BAR_LEFT + 1, 4, 100, 9))

        oled.show_usage({"five_hour": {"utilization": 90}})
        high = lit_pixels(oled.device.image, (oled.BAR_LEFT + 1, 4, 100, 9))

        assert high > low

    def test_utilization_is_clamped(self, oled):
        oled.show_usage({"five_hour": {"utilization": 100}})
        full = oled.device.image.copy()

        oled.show_usage({"five_hour": {"utilization": 250}})

        assert ImageChops.difference(full, oled.device.image).getbbox() is None

    def test_expired_window_shows_empty_bar(self, oled):
        oled.show_usage({"five_hour": {"utilization": 0}})
        empty = oled.device.image.copy()

        oled.show_usage(
            {"five_hour": {"utilization": 90, "resets_at": "2026-11-24T11:59:00+00:00"}}
        )

        assert ImageChops.difference(empty, oled.device.image).getbbox() is None

    def test_old_data_replaces_weekly_reset(self, oled):
        oled.show_usage(USAGE)
        weekly_reset = oled.device.image.crop((0, 48, 128, 64))

        oled.show_usage(USAGE, updated_at=datetime.datetime(2026, 11, 24, 11, 0))

        changed = ImageChops.difference(weekly_reset, oled.device.image.crop((0, 48, 128, 64)))
        assert changed.getbbox() is not None

    def test_missing_data(self, oled):
        oled.show_usage({"five_hour": None})
        empty = oled.device.image.copy()

        oled.show_usage({"five_hour": {"utilization": 0}, "seven_day": {}})

        assert ImageChops.difference(empty, oled.device.image).getbbox() is None
