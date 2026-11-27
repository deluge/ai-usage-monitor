"""
Start the display on the Raspberry Pi. Your main.py (see README_RASPBERRY_PI.md) calls main().

The settings are read from ~/.usage-monitor/settings.json (see display_usage/settings.py).
"""

import os

from display_usage.pizerow.display import Oled_m154_7p
from display_usage.settings import build_monitor, load_settings


SETTINGS_FILE = "~/.usage-monitor/settings.json"


def main(settings_file=SETTINGS_FILE):
    settings = load_settings(os.path.expanduser(settings_file))
    build_monitor(settings, Oled_m154_7p).run()
