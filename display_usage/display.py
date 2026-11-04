from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1309

from display_usage.utils import (
    format_reset_current,
    format_reset_weekly,
    load_font,
    parse_reset,
)


CONTROLLERS = {"ssd1306": ssd1306, "ssd1309": ssd1309}


class BaseDisplay:
    def show_message(self, *lines):
        raise NotImplementedError

    def show_loading(self, dots=3):
        with canvas(self.device) as draw:
            draw.text((0, 26), "Loading" + "." * dots, font=self.font, fill="white")

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
        controller="ssd1309",
        contrast=200,
        rotate=0,
        gpio_data_command=24,
        gpio_reset=25,
        spi_port=0,
        spi_device=0,
        bus_speed_hz=8_000_000,
    ):
        serial = spi(
            port=spi_port,
            device=spi_device,
            gpio_DC=gpio_data_command,
            gpio_RST=gpio_reset,
            bus_speed_hz=bus_speed_hz,
        )
        self.device = CONTROLLERS[controller](
            serial, width=self.WIDTH, height=self.HEIGHT, rotate=rotate
        )
        self.device.contrast(contrast)
        self.font = load_font(11)
        self.font_small = load_font(10)

    def show_message(self, *lines):
        with canvas(self.device) as draw:
            for i, line in enumerate(lines):
                draw.text((0, i * self.LINE_HEIGHT), line, font=self.font, fill="white")

    def show_usage(self, usage):
        five_hour = usage.get("five_hour") or {}
        seven_day = usage.get("seven_day") or {}
        current_reset = format_reset_current(parse_reset(five_hour.get("resets_at")))
        weekly_reset = format_reset_weekly(parse_reset(seven_day.get("resets_at")))
        with canvas(self.device) as draw:
            self._draw_block(draw, 0, "Current", five_hour.get("utilization"), current_reset)
            draw.line((0, 31, self.WIDTH - 1, 31), fill="white")
            self._draw_block(draw, 34, "Weekly", seven_day.get("utilization"), weekly_reset)

    def _draw_block(self, draw, top, label, percent, reset_text):
        """Draw "label [bar] xx%" with the reset time in the line below."""
        percent = max(0.0, min(100.0, percent or 0.0))
        percent_text = f"{percent:.0f}%"
        percent_left = self.WIDTH - draw.textlength(percent_text, font=self.font)

        draw.text((0, top), label, font=self.font, fill="white")
        self._draw_bar(draw, top + 3, right=percent_left - 4, percent=percent)
        draw.text((percent_left, top), percent_text, font=self.font, fill="white")
        draw.text((0, top + self.LINE_HEIGHT), reset_text, font=self.font_small, fill="white")

    def _draw_bar(self, draw, top, right, percent):
        left, bottom = self.BAR_LEFT, top + self.BAR_HEIGHT
        draw.rectangle((left, top, right, bottom), outline="white")
        fill_width = int((right - left - 2) * percent / 100)
        if fill_width > 0:
            draw.rectangle((left + 1, top + 1, left + 1 + fill_width, bottom - 1), fill="white")
