import json
import os

from display_usage.pizerow import app
from display_usage.pizerow.display import Oled_m154_7p


class FakeMonitor:
    ran = False

    def run(self):
        self.ran = True


def test_main_reads_settings_and_runs(monkeypatch, tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"display": {"rotate": 2}}))
    built = {}

    def fake_build_monitor(settings, display_class, wifi_class=None):
        built.update(settings=settings, display_class=display_class, wifi_class=wifi_class)
        built["cwd"] = os.getcwd()
        built["monitor"] = FakeMonitor()
        return built["monitor"]

    monkeypatch.setattr(app, "build_monitor", fake_build_monitor)
    monkeypatch.chdir(tmp_path)

    app.main(str(settings_file))

    assert built["settings"] == {"display": {"rotate": 2}}
    assert built["display_class"] is Oled_m154_7p
    assert built["wifi_class"] is None
    assert built["cwd"] == app.PROJECT_DIR
    assert built["monitor"].ran


def test_files_are_in_the_project_folder():
    assert os.path.isfile(os.path.join(app.PROJECT_DIR, "pyproject.toml"))
    assert app.SETTINGS_FILE == "settings.json"
