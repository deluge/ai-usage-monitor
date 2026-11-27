import json

import pytest


class FakeMonitor:
    ran = False

    def run(self):
        self.ran = True


@pytest.fixture
def app_module(micropython_modules):
    from display_usage.esp32 import app

    return app


@pytest.fixture
def built(monkeypatch, app_module):
    built = {}

    def fake_build_monitor(settings, display_class, wifi_class=None):
        built.update(settings=settings, display_class=display_class, wifi_class=wifi_class)
        built["monitor"] = FakeMonitor()
        return built["monitor"]

    monkeypatch.setattr(app_module, "build_monitor", fake_build_monitor)
    return built


def test_main_reads_settings_and_runs(app_module, built, tmp_path):
    from display_usage.esp32.display import Oled_m154_7p
    from display_usage.esp32.wifi import Wifi

    settings = {"wifi": {"ssid": "Home", "password": "secret"}}
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps(settings))

    app_module.main(str(settings_file))

    assert built["settings"] == settings
    assert built["display_class"] is Oled_m154_7p
    assert built["wifi_class"] is Wifi
    assert built["monitor"].ran


def test_main_logs_missing_settings(app_module, built, tmp_path, capsys):
    app_module.main(str(tmp_path / "settings.json"))

    assert "settings.json is missing" in capsys.readouterr().err
    assert built["settings"] == {}
