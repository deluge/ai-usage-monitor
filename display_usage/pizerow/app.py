"""
Start the display on the Raspberry Pi. Your main.py (see README_RASPBERRY_PI.md) calls main().

settings.json and credentials.json are read from the project folder (see settings.py).
"""

import os

from display_usage.pizerow.display import Oled_m154_7p
from display_usage.settings import build_monitor, load_settings


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SETTINGS_FILE = "settings.json"


def main(settings_file=SETTINGS_FILE):
    # Relative paths (settings.json, credentials.json) are relative to the project folder,
    # wherever main.py is started from.
    os.chdir(PROJECT_DIR)
    settings = load_settings(settings_file)
    build_monitor(settings, Oled_m154_7p).run()
