"""
Settings file of the start scripts (display_usage/pizerow/app.py, display_usage/esp32/app.py).

A JSON object with one section per class; each section holds the keyword arguments
of that class, so the settings are the ones listed in the READMEs:

  {"wifi": {"ssid": "...", "password": "..."},      (ESP32 only)
   "timezone": {"utc_offset": 1, "dst": "eu"},
   "display": {"contrast": 200},
   "api": {"timeout": 20},
   "monitor": {"api_request_interval": 120}}

Every section is optional, except "wifi" on the ESP32.
"""

import json

from display_usage.api import ClaudeApi
from display_usage.errors import SettingsError
from display_usage.monitor import UsageMonitor
from display_usage.utils import Timezone


SECTIONS = ("wifi", "timezone", "display", "api", "monitor")


def load_settings(path):
    """Read the settings file; a missing file means all defaults."""
    try:
        with open(path) as settings_handle:
            settings = json.load(settings_handle)
    except OSError:
        return {}
    except ValueError as error:
        raise SettingsError(f"{path} is not valid JSON: {error}")
    if not isinstance(settings, dict):
        raise SettingsError(f"{path} must contain a JSON object")
    for section, values in settings.items():
        if section not in SECTIONS:
            raise SettingsError(f"Unknown section {section!r} in {path}")
        if not isinstance(values, dict):
            raise SettingsError(f"Section {section!r} in {path} must be a JSON object")
    return settings


def create(cls, settings, section, **arguments):
    """Create cls with the settings of the section, reporting misspelled settings clearly."""
    arguments.update(settings.get(section, {}))
    try:
        return cls(**arguments)
    except (TypeError, ValueError) as error:  # unknown setting or invalid value
        raise SettingsError(f"Section {section!r}: {error}")


def build_monitor(settings, display_class, wifi_class=None):
    """Create the UsageMonitor with its Wi-Fi, API and display from the settings."""
    wifi = None
    if wifi_class is not None:
        if "wifi" not in settings:
            raise SettingsError("The settings need a 'wifi' section with ssid and password")
        wifi = create(wifi_class, settings, "wifi")
    elif "wifi" in settings:
        raise SettingsError("This board doesn't use the 'wifi' section")
    api = create(ClaudeApi, settings, "api")
    timezone = create(Timezone, settings, "timezone")
    display = create(display_class, settings, "display", timezone=timezone)
    return create(UsageMonitor, settings, "monitor", api=api, oled=display, wifi=wifi)
