import json

import pytest

from display_usage.api import ClaudeApi
from display_usage.errors import SettingsError
from display_usage.monitor import UsageMonitor
from display_usage.settings import build_monitor, load_settings
from display_usage.utils import Timezone


class RecordingDisplay:
    def __init__(self, timezone=None, contrast=200, flip=False):
        self.timezone, self.contrast, self.flip = timezone, contrast, flip


class RecordingWifi:
    def __init__(self, ssid, password, tx_power=None):
        self.ssid, self.password, self.tx_power = ssid, password, tx_power


@pytest.fixture
def settings_file(tmp_path):
    def write(content):
        path = tmp_path / "settings.json"
        path.write_text(content if isinstance(content, str) else json.dumps(content))
        return str(path)

    return write


def test_load_settings(settings_file):
    settings = {"display": {"flip": True}, "timezone": {"utc_offset": 1, "dst": "eu"}}

    assert load_settings(settings_file(settings)) == settings


def test_load_settings_missing_file_means_defaults(tmp_path):
    assert load_settings(str(tmp_path / "missing.json")) == {}


@pytest.mark.parametrize(
    "content, message",
    [
        ("{not json", "not valid JSON"),
        ("[]", "must contain a JSON object"),
        ({"displya": {}}, "Unknown section 'displya'"),
        ({"display": True}, "Section 'display' in .* must be a JSON object"),
    ],
)
def test_load_settings_errors(settings_file, content, message):
    with pytest.raises(SettingsError, match=message):
        load_settings(settings_file(content))


def test_build_monitor_with_defaults():
    monitor = build_monitor({}, RecordingDisplay)

    assert isinstance(monitor, UsageMonitor)
    assert isinstance(monitor.api, ClaudeApi)
    assert monitor.wifi is None
    assert isinstance(monitor.oled, RecordingDisplay)
    assert monitor.oled.timezone.utc_offset is None
    assert monitor.api_request_interval == 120


def test_build_monitor_passes_every_section():
    settings = {
        "wifi": {"ssid": "Home", "password": "secret", "tx_power": 8.5},
        "timezone": {"utc_offset": 1, "dst": "eu"},
        "display": {"contrast": 50, "flip": True},
        "api": {"credentials_file": "/tmp/login.json", "timeout": 5},
        "monitor": {"api_request_interval": 300, "display_refresh_interval": 10},
    }

    monitor = build_monitor(settings, RecordingDisplay, RecordingWifi)

    wifi, display = monitor.wifi, monitor.oled
    assert (wifi.ssid, wifi.password, wifi.tx_power) == ("Home", "secret", 8.5)
    assert isinstance(display.timezone, Timezone)
    assert (display.timezone.utc_offset, display.timezone.dst) == (3600, "eu")
    assert (display.contrast, display.flip) == (50, True)
    assert (monitor.api.credentials_file, monitor.api.timeout) == ("/tmp/login.json", 5)
    assert (monitor.api_request_interval, monitor.display_refresh_interval) == (300, 10)


def test_build_monitor_needs_wifi_on_esp32():
    with pytest.raises(SettingsError, match="'wifi' section"):
        build_monitor({}, RecordingDisplay, RecordingWifi)


def test_build_monitor_rejects_wifi_on_pi():
    with pytest.raises(SettingsError, match="doesn't use the 'wifi' section"):
        build_monitor({"wifi": {"ssid": "Home", "password": "secret"}}, RecordingDisplay)


@pytest.mark.parametrize(
    "settings, message",
    [
        ({"display": {"flipp": True}}, "Section 'display': .*flipp"),
        ({"timezone": {"dst": "asia"}}, "Section 'timezone': dst must be"),
        ({"monitor": {"interval": 60}}, "Section 'monitor': .*interval"),
    ],
)
def test_build_monitor_reports_wrong_settings(settings, message):
    with pytest.raises(SettingsError, match=message):
        build_monitor(settings, RecordingDisplay)
