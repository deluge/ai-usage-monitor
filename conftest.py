import json
import time

import pytest

from display_usage import api as api_module
from display_usage.api import ClaudeApi
from testing.fakes import micropython
from testing.fakes.api import FakeServer
from testing.fakes.display import FakeDisplay


# 2026-11-24 12:00:00 UTC, the time all tests using freezegun run at.
NOW = 1795521600


@pytest.fixture(autouse=True)
def utc_timezone(monkeypatch):
    """Run every test in UTC, like the CI, whatever the local timezone is."""
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


@pytest.fixture
def credentials_file(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text(
        json.dumps(
            {
                "claudeAiOauth": {
                    "accessToken": "old-access",
                    "refreshToken": "old-refresh",
                    "expiresAt": (NOW + 3600) * 1000,
                }
            }
        )
    )
    return path


@pytest.fixture
def read_credentials(credentials_file):
    def read():
        return json.loads(credentials_file.read_text())["claudeAiOauth"]

    return read


@pytest.fixture
def server(monkeypatch):
    server = FakeServer()
    monkeypatch.setattr(api_module.requests, "request", server)
    return server


@pytest.fixture
def api(credentials_file, server):
    return ClaudeApi(credentials_file=str(credentials_file))


@pytest.fixture
def display():
    return FakeDisplay()


@pytest.fixture
def micropython_modules(monkeypatch):
    """Fake machine, network, framebuf, ... modules; returns (clock, network)."""
    return micropython.install(monkeypatch)
