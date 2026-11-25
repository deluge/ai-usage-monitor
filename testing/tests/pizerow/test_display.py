import pytest
from freezegun import freeze_time
from luma.core.device import dummy
from PIL import ImageChops, ImageFont

from display_usage.pizerow import display as display_module
from display_usage.pizerow.display import Oled_m154_7p, load_font
from display_usage.utils import Timezone


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


class TestLoadFont:
    def test_truetype_font(self, monkeypatch, tmp_path):
        font_file = tmp_path / "DejaVuSans-Bold.ttf"
        font_file.touch()
        loaded = []
        monkeypatch.setattr(display_module, "FONT_DIRECTORY", f"{tmp_path}/")
        monkeypatch.setattr(ImageFont, "truetype", lambda *args: loaded.append(args))

        load_font(11)

        assert loaded == [(str(font_file), 11)]

    def test_default_font(self, monkeypatch, tmp_path):
        monkeypatch.setattr(display_module, "FONT_DIRECTORY", f"{tmp_path}/")

        assert isinstance(load_font(11), ImageFont.ImageFont | ImageFont.FreeTypeFont)


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
    assert oled.timezone.utc_offset is None
    assert oled.image.size == (128, 64)


def test_init_with_timezone(fake_hardware):
    timezone = Timezone(1)

    assert Oled_m154_7p(timezone=timezone).timezone is timezone


def test_unknown_controller(fake_hardware):
    with pytest.raises(KeyError):
        Oled_m154_7p(controller="unknown")


def test_nothing_shown_before_show(oled):
    oled.text(0, 0, "Hello", oled.font)

    assert oled.device.image is None


def test_show_loading(oled):
    oled.show_loading(1)
    one_dot = oled.device.image.copy()

    oled.show_loading()

    assert lit_pixels(oled.device.image) > lit_pixels(one_dot)


def test_clear(oled):
    oled.show_loading()

    oled.clear()
    oled.show()

    assert lit_pixels(oled.device.image) == 0


def test_show_message(oled):
    oled.show_message("First", "", "Third")

    image = oled.device.image
    assert lit_pixels(image, (0, 0, 128, 14)) > 0
    assert lit_pixels(image, (0, 14, 128, 28)) == 0
    assert lit_pixels(image, (0, 28, 128, 42)) > 0


def test_textlength(oled):
    assert 0 < oled.textlength("Hi", oled.font) < oled.textlength("Hello", oled.font)


def test_rectangle(oled):
    oled.clear()
    oled.rectangle(10, 10, 19, 14)
    oled.rectangle(30, 10, 39, 14, fill=True)
    oled.show()

    image = oled.device.image
    assert lit_pixels(image, (10, 10, 20, 15)) == 2 * 10 + 2 * 3  # outline only
    assert lit_pixels(image, (30, 10, 40, 15)) == 10 * 5


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
        low = lit_pixels(oled.device.image, (oled.BAR_LEFT + 1, 4, 100, 10))

        oled.show_usage({"five_hour": {"utilization": 90}})
        high = lit_pixels(oled.device.image, (oled.BAR_LEFT + 1, 4, 100, 10))

        assert high > low

    def test_missing_data(self, oled):
        oled.show_usage({"five_hour": None})
        empty = oled.device.image.copy()

        oled.show_usage({"five_hour": {"utilization": 0}, "seven_day": {}})

        assert ImageChops.difference(empty, oled.device.image).getbbox() is None
