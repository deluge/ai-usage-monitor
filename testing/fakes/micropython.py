"""Fakes for the MicroPython modules the ESP32 code imports.

install() puts them into sys.modules, so display_usage.esp32 can be imported
and tested with CPython.
"""

import sys
import time
import types


class FrameBuffer:
    """Monochrome framebuffer storing its pixels in a set of lit (x, y) positions."""

    def __init__(self, buffer, width, height, format=None):
        self.width = width
        self.height = height
        self.pixels = set()
        if format == MONO_HLSB:
            row_bytes = (width + 7) // 8
            for y in range(height):
                for x in range(width):
                    if buffer[y * row_bytes + x // 8] & (0x80 >> (x % 8)):
                        self.pixels.add((x, y))

    def fill(self, color):
        self.pixels = (
            {(x, y) for x in range(self.width) for y in range(self.height)} if color else set()
        )

    def fill_rect(self, x, y, width, height, color):
        for column in range(x, x + width):
            for row in range(y, y + height):
                self.pixel(column, row, color)

    def rect(self, x, y, width, height, color):
        for column in range(x, x + width):
            self.pixel(column, y, color)
            self.pixel(column, y + height - 1, color)
        for row in range(y, y + height):
            self.pixel(x, row, color)
            self.pixel(x + width - 1, row, color)

    def pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            if color:
                self.pixels.add((x, y))
            else:
                self.pixels.discard((x, y))

    def blit(self, source, x, y, key=-1):
        for source_x, source_y in source.pixels:
            self.pixel(x + source_x, y + source_y, 1)


MONO_HLSB = "MONO_HLSB"


class SSD1306_SPI(FrameBuffer):
    def __init__(self, width, height, spi, dc, res, cs):
        super().__init__(bytearray(), width, height)
        self.spi, self.dc, self.res, self.cs = spi, dc, res, cs
        self.settings = {}
        self.shown = 0
        self.commands = []
        self.init_display()

    def init_display(self):
        self.commands.append("default init")

    def write_cmd(self, command):
        self.commands.append(command)

    def contrast(self, level):
        self.settings["contrast"] = level

    def rotate(self, flip):
        self.settings["rotate"] = flip

    def show(self):
        self.shown += 1


class Pin:
    def __init__(self, number):
        self.number = number

    def __eq__(self, other):
        return isinstance(other, Pin) and other.number == self.number

    def __repr__(self):
        return f"Pin({self.number})"


class SPI:
    def __init__(self, bus, baudrate, sck, mosi):
        self.bus, self.baudrate, self.sck, self.mosi = bus, baudrate, sck, mosi


class WLAN:
    def __init__(self, interface):
        self.interface = interface
        self.is_active = False
        self.settings = {}
        self.connected = False
        self.state = STAT_IDLE
        self.connect_calls = []
        self.connect_error = None

    def active(self, is_active):
        self.is_active = is_active

    def config(self, **settings):
        self.settings.update(settings)

    def isconnected(self):
        return self.connected

    def status(self):
        return self.state

    def connect(self, ssid, password):
        self.connect_calls.append((ssid, password))
        if self.connect_error:
            raise self.connect_error


STA_IF = 0
STAT_IDLE = 1000
STAT_CONNECTING = 1001
STAT_WRONG_PASSWORD = 202
STAT_NO_AP_FOUND = 201


class Clock:
    """Stands in for time.ticks_ms() and ntptime.settime()."""

    def __init__(self):
        self.ms = 0
        self.synced = 0

    def ticks_ms(self):
        return self.ms

    @staticmethod
    def ticks_diff(new, old):
        return new - old

    def settime(self):
        self.synced += 1


def install(monkeypatch):
    """Put the fake modules into sys.modules and return the clock and network module."""
    clock = Clock()
    network = types.ModuleType("network")
    network.WLAN = WLAN
    network.STA_IF = STA_IF
    network.STAT_IDLE = STAT_IDLE
    network.STAT_CONNECTING = STAT_CONNECTING
    network.STAT_WRONG_PASSWORD = STAT_WRONG_PASSWORD
    network.STAT_NO_AP_FOUND = STAT_NO_AP_FOUND
    network.hostnames = []
    network.hostname = network.hostnames.append

    modules = {
        "framebuf": types.SimpleNamespace(FrameBuffer=FrameBuffer, MONO_HLSB=MONO_HLSB),
        "machine": types.SimpleNamespace(Pin=Pin, SPI=SPI),
        "ssd1306": types.SimpleNamespace(SSD1306_SPI=SSD1306_SPI),
        "network": network,
        "ntptime": types.SimpleNamespace(settime=clock.settime),
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    # Forget the modules imported with the fakes of an earlier test, so they are
    # imported again with these ones (also from the package, where a submodule is
    # cached as an attribute after its first import).
    import display_usage.esp32

    for name in ("display", "font", "wifi"):
        monkeypatch.delitem(sys.modules, f"display_usage.esp32.{name}", raising=False)
        monkeypatch.delattr(display_usage.esp32, name, raising=False)

    monkeypatch.setattr(time, "ticks_ms", clock.ticks_ms, raising=False)
    monkeypatch.setattr(time, "ticks_diff", clock.ticks_diff, raising=False)
    return clock, network
