import ssd1306
from machine import SPI, Pin

from display_usage import dejavu_sans_10, dejavu_sans_11
from display_usage.font import BitmapFont
from display_usage.utils import (
    Timezone,
    format_reset_current,
    format_reset_weekly,
    parse_reset,
)


class BaseDisplay:
    def show_message(self, *lines):
        raise NotImplementedError

    def show_loading(self, dots=3):
        self.device.fill(0)
        self.font.text(self.device, "Loading" + "." * dots, 0, 26)
        self.device.show()

    def show_usage(self, usage):
        raise NotImplementedError


class Oled_m154_7p(BaseDisplay):
    WIDTH = 128
    HEIGHT = 64
    LINE_HEIGHT = 14
    BAR_LEFT = 52  # leaves room for the "Current" / "Weekly" label
    BAR_HEIGHT = 7

    def __init__(
        self,
        timezone=None,
        contrast=200,
        flip=False,
        gpio_clock=6,
        gpio_data=7,
        gpio_chip_select=10,
        gpio_data_command=5,
        gpio_reset=4,
        spi_bus=1,
        bus_speed_hz=8_000_000,
    ):
        serial = SPI(spi_bus, baudrate=bus_speed_hz, sck=Pin(gpio_clock), mosi=Pin(gpio_data))
        self.device = ssd1306.SSD1306_SPI(
            self.WIDTH,
            self.HEIGHT,
            serial,
            dc=Pin(gpio_data_command),
            res=Pin(gpio_reset),
            cs=Pin(gpio_chip_select),
        )
        self.device.contrast(contrast)
        self.device.rotate(flip)
        self.timezone = timezone or Timezone()
        self.font = BitmapFont(dejavu_sans_11)
        self.font_small = BitmapFont(dejavu_sans_10)

    def show_message(self, *lines):
        self.device.fill(0)
        for i, line in enumerate(lines):
            self.font.text(self.device, line, 0, i * self.LINE_HEIGHT)
        self.device.show()

    def show_usage(self, usage):
        five_hour = usage.get("five_hour") or {}
        seven_day = usage.get("seven_day") or {}
        current_reset = format_reset_current(
            parse_reset(five_hour.get("resets_at")), self.timezone
        )
        weekly_reset = format_reset_weekly(
            parse_reset(seven_day.get("resets_at")), self.timezone
        )
        self.device.fill(0)
        self._draw_block(0, "Current", five_hour.get("utilization"), current_reset)
        self.device.hline(0, 31, self.WIDTH, 1)
        self._draw_block(34, "Weekly", seven_day.get("utilization"), weekly_reset)
        self.device.show()

    def _draw_block(self, top, label, percent, reset_text):
        """Draw "label [bar] xx%" with the reset time in the line below."""
        percent = max(0.0, min(100.0, percent or 0.0))
        percent_text = f"{percent:.0f}%"
        percent_left = self.WIDTH - self.font.textlength(percent_text)

        self.font.text(self.device, label, 0, top)
        self._draw_bar(top + 3, right=percent_left - 4, percent=percent)
        self.font.text(self.device, percent_text, percent_left, top)
        self.font_small.text(self.device, reset_text, 0, top + self.LINE_HEIGHT)

    def _draw_bar(self, top, right, percent):
        left = self.BAR_LEFT
        self.device.rect(left, top, right - left + 1, self.BAR_HEIGHT + 1, 1)
        fill_width = int((right - left - 2) * percent / 100)
        if fill_width > 0:
            # +1 because PIL's rectangle, used on the Pi, includes both end points.
            self.device.fill_rect(left + 1, top + 1, fill_width + 1, self.BAR_HEIGHT - 1, 1)
