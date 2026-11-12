import ssd1306
from machine import SPI, Pin

from display_usage.display import BaseDisplay
from display_usage.esp32 import dejavu_sans_10, dejavu_sans_11
from display_usage.esp32.font import BitmapFont


class Oled_m154_7p(BaseDisplay):
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
        super().__init__(timezone)
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
        # The same font and sizes as on the Pi, pre-rendered by tools/make_esp32_fonts.py.
        self.font = BitmapFont(dejavu_sans_11)
        self.font_small = BitmapFont(dejavu_sans_10)

    def clear(self):
        self.device.fill(0)

    def show(self):
        self.device.show()

    def text(self, x, y, text, font):
        font.draw(self.device, x, y, text)

    def textlength(self, text, font):
        return font.textlength(text)

    def rectangle(self, left, top, right, bottom, fill=False):
        width, height = right - left + 1, bottom - top + 1
        if fill:
            self.device.fill_rect(left, top, width, height, 1)
        else:
            self.device.rect(left, top, width, height, 1)
