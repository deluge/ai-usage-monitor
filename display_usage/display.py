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
                draw.text((0, i * 14), line, font=self.font, fill="white")

    def _draw_block(self, draw, top, label, percent, reset_text):
        percent = max(0.0, min(100.0, percent or 0.0))
        draw.text((0, top), label, font=self.font, fill="white")
        percent_text = f"{percent:.0f}%"
        percent_width = draw.textlength(percent_text, font=self.font)
        draw.text((self.WIDTH - percent_width, top), percent_text, font=self.font, fill="white")
        bar_x, bar_y, bar_height = 52, top + 3, 7
        bar_width = self.WIDTH - percent_width - 56
        draw.rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + bar_height), outline="white")
        fill_width = int((bar_width - 2) * percent / 100)
        if fill_width > 0:
            draw.rectangle(
                (bar_x + 1, bar_y + 1, bar_x + 1 + fill_width, bar_y + bar_height - 1),
                fill="white",
            )
        draw.text((0, top + 14), reset_text, font=self.font_small, fill="white")

    def show_usage(self, usage):
        five_hour = usage.get("five_hour") or {}
        seven_day = usage.get("seven_day") or {}
        with canvas(self.device) as draw:
            self._draw_block(
                draw,
                0,
                "Current",
                five_hour.get("utilization"),
                format_reset_current(parse_reset(five_hour.get("resets_at"))),
            )
            draw.line((0, 31, self.WIDTH - 1, 31), fill="white")
            self._draw_block(
                draw,
                34,
                "Weekly",
                seven_day.get("utilization"),
                format_reset_weekly(parse_reset(seven_day.get("resets_at"))),
            )
