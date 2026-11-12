import os

from luma.core.interface.serial import spi
from luma.oled.device import ssd1306, ssd1309
from PIL import Image, ImageDraw, ImageFont

from display_usage.display import BaseDisplay


CONTROLLERS = {"ssd1306": ssd1306, "ssd1309": ssd1309}
FONT_DIRECTORY = "/usr/share/fonts/truetype/dejavu/"


def load_font(size, names=("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")):
    for name in names:
        path = FONT_DIRECTORY + name
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


class Oled_m154_7p(BaseDisplay):
    def __init__(
        self,
        timezone=None,
        controller="ssd1309",
        contrast=200,
        rotate=0,
        gpio_data_command=24,
        gpio_reset=25,
        spi_port=0,
        spi_device=0,
        bus_speed_hz=8_000_000,
    ):
        super().__init__(timezone)
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
        self.font = load_font(self.FONT_SIZE)
        self.font_small = load_font(self.SMALL_FONT_SIZE)
        self.clear()

    def clear(self):
        self.image = Image.new(self.device.mode, self.device.size)
        self.draw = ImageDraw.Draw(self.image)

    def show(self):
        self.device.display(self.image)

    def text(self, x, y, text, font):
        self.draw.text((x, y), text, font=font, fill="white")

    def textlength(self, text, font):
        return self.draw.textlength(text, font=font)

    def rectangle(self, left, top, right, bottom, fill=False):
        self.draw.rectangle(
            (left, top, right, bottom), outline="white", fill="white" if fill else None
        )
