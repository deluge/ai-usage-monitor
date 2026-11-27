import ssd1306
from machine import SPI, Pin

from display_usage.display import BaseDisplay
from display_usage.esp32 import dejavu_sans_10, dejavu_sans_11
from display_usage.esp32.font import BitmapFont


# The init sequence of luma.oled, which the Pi uses. MicroPython's ssd1306 driver
# also sends 0xAD 0x30 (internal IREF, an SSD1306 command), which makes an SSD1309
# show grey vertical streaks below lit pixels.
SSD1309_INIT = (
    0xAE,  # display off
    0xD5, 0x80,  # clock divide ratio / oscillator frequency
    0xA8, 0x3F,  # multiplex ratio: 64 rows
    0xD3, 0x00,  # display offset
    0x40,  # start line 0
    0x8D, 0x14,  # charge pump on (ignored by the SSD1309)
    0x20, 0x00,  # horizontal addressing mode
    0xA1,  # segment remap
    0xC8,  # COM scan direction: remapped
    0xDA, 0x12,  # COM pins configuration
    0xD9, 0xF1,  # pre-charge period
    0xDB, 0x40,  # VCOMH deselect level
    0xA4,  # output follows RAM contents
    0xA6,  # not inverted
    0xAF,  # display on
)  # fmt: skip


class SSD1309_SPI(ssd1306.SSD1306_SPI):
    def init_display(self):
        # Called by the driver's constructor, right after the hardware reset.
        for command in SSD1309_INIT:
            self.write_cmd(command)
        self.fill(0)
        self.show()


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
        self.device = SSD1309_SPI(
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
