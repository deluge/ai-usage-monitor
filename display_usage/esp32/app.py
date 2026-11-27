"""
Start the display on the ESP32. Your main.py (see README_ESP32_C3.md) calls main().

The settings are read from settings.json on the board (see display_usage/settings.py).
"""

from display_usage.esp32.display import Oled_m154_7p
from display_usage.esp32.wifi import Wifi
from display_usage.settings import build_monitor, load_settings
from display_usage.utils import log


SETTINGS_FILE = "settings.json"


def main(settings_file=SETTINGS_FILE):
    settings = load_settings(settings_file)
    if not settings:
        log(f"{settings_file} is missing: copy it to the board (make esp32-settings)")
    build_monitor(settings, Oled_m154_7p, Wifi).run()
