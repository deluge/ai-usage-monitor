import json
import os
import stat

import pytest
from freezegun import freeze_time

from conftest import NOW
from display_usage import api as api_module
from display_usage.api import (
    CLIENT_ID,
    TOKEN_URLS,
    USAGE_URL,
    USER_AGENT,
    ClaudeApi,
    expand_user,
)
from display_usage.errors import CredentialsMissing, HttpError
from testing.fakes.api import FakeResponse


USAGE = {"five_hour": {"utilization": 12.0}, "seven_day": {"utilization": 34.0}}
TOKEN = {"access_token": "new-access", "refresh_token": "new-refresh", "expires_in": 7200}


def expire_token(credentials_file, expires_at=NOW):
    data = json.loads(credentials_file.read_text())
    data["claudeAiOauth"]["expiresAt"] = expires_at * 1000
    credentials_file.write_text(json.dumps(data))


def test_default_credentials_file():
    api = ClaudeApi()

    assert api.credentials_file == "~/.usage-monitor/credentials.json"
    assert api.credentials_path == os.path.expanduser("~/.usage-monitor/credentials.json")


def test_expand_user_without_os_path(monkeypatch):
    real_import = __import__

    def no_os_path(name, *args, **kwargs):
        if name == "os.path":
            raise ImportError
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", no_os_path)

    assert expand_user("~/creds.json") == "~/creds.json"


def test_missing_credentials_file(tmp_path, server):
    api = ClaudeApi(credentials_file=str(tmp_path / "missing.json"))

    with pytest.raises(CredentialsMissing) as error:
        api.fetch_usage()

    assert str(error.value) == str(tmp_path / "missing.json")
    assert server.requests == []


class TestRequestJson:
    def test_get(self, api, server):
        server.add(USAGE_URL, USAGE)

        assert api.request_json(USAGE_URL, headers={"X-Test": "1"}) == USAGE

        request = server.requests[0]
        assert request.method == "GET"
        assert request.data is None
        assert request.timeout == 20
        assert request.headers == {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "X-Test": "1",
        }
        assert server.sent[0].closed

    def test_post(self, api, server):
        server.add(TOKEN_URLS[0], TOKEN)

        api.request_json(TOKEN_URLS[0], body={"a": 1})

        assert server.requests[0].method == "POST"
        assert server.requests[0].json() == {"a": 1}

    def test_error(self, api, server):
        response = FakeResponse(429, text="x" * 600, headers={"Retry-After": "30"})
        server.add(USAGE_URL, response)

        with pytest.raises(HttpError) as error:
            api.request_json(USAGE_URL)

        assert (error.value.code, error.value.url) == (429, USAGE_URL)
        assert error.value.body == "x" * 500
        assert error.value.headers == {"retry-after": "30"}
        assert str(error.value) == "HTTP 429"
        assert response.closed


@freeze_time("2026-11-24 12:00:00")
class TestFetchUsage:
    def test_valid_token(self, api, server):
        server.add(USAGE_URL, USAGE)

        assert api.fetch_usage() == USAGE

        headers = server.requests[0].headers
        assert headers["Authorization"] == "Bearer old-access"
        assert headers["anthropic-beta"] == "oauth-2025-04-20"

    def test_refreshes_expiring_token(self, api, server, credentials_file, read_credentials):
        expire_token(credentials_file, NOW + 60)
        server.add(TOKEN_URLS[0], TOKEN)
        server.add(USAGE_URL, USAGE)

        assert api.fetch_usage() == USAGE

        assert server.urls() == [TOKEN_URLS[0], USAGE_URL]
        assert server.requests[0].json() == {
            "grant_type": "refresh_token",
            "refresh_token": "old-refresh",
            "client_id": CLIENT_ID,
        }
        assert server.requests[1].headers["Authorization"] == "Bearer new-access"
        assert read_credentials() == {
            "accessToken": "new-access",
            "refreshToken": "new-refresh",
            "expiresAt": (NOW + 7200) * 1000,
        }

    def test_refresh_keeps_refresh_token_and_defaults_expiry(
        self, api, server, credentials_file, read_credentials
    ):
        expire_token(credentials_file)
        server.add(TOKEN_URLS[0], {"access_token": "new-access"})
        server.add(USAGE_URL, USAGE)

        api.fetch_usage()

        assert read_credentials() == {
            "accessToken": "new-access",
            "refreshToken": "old-refresh",
            "expiresAt": (NOW + 3600) * 1000,
        }

    def test_credentials_file_permissions(self, api, server, credentials_file):
        expire_token(credentials_file)
        server.add(TOKEN_URLS[0], TOKEN)
        server.add(USAGE_URL, USAGE)

        api.fetch_usage()

        assert stat.S_IMODE(credentials_file.stat().st_mode) == 0o600
        assert not os.path.exists(f"{credentials_file}.tmp")

    def test_credentials_without_chmod(self, api, server, credentials_file, monkeypatch):
        """MicroPython's os has no chmod."""
        monkeypatch.delattr(api_module.os, "chmod")
        expire_token(credentials_file)
        server.add(TOKEN_URLS[0], TOKEN)
        server.add(USAGE_URL, USAGE)

        assert api.fetch_usage() == USAGE

    @pytest.mark.parametrize("code", [400, 401, 403, 404, 500])
    def test_refresh_falls_back_to_next_token_url(self, api, server, credentials_file, code):
        expire_token(credentials_file)
        server.add(TOKEN_URLS[0], code)
        server.add(TOKEN_URLS[1], TOKEN)
        server.add(USAGE_URL, USAGE)

        assert api.fetch_usage() == USAGE

        assert server.urls() == [TOKEN_URLS[0], TOKEN_URLS[1], USAGE_URL]

    def test_refresh_stops_on_rate_limit(self, api, server, credentials_file):
        expire_token(credentials_file)
        server.add(TOKEN_URLS[0], 429)

        with pytest.raises(HttpError) as error:
            api.fetch_usage()

        assert error.value.code == 429
        assert server.urls() == [TOKEN_URLS[0]]

    def test_refresh_fails_everywhere_with_expired_token(
        self, api, server, credentials_file, read_credentials
    ):
        expire_token(credentials_file)
        server.add(TOKEN_URLS[0], 400)
        server.add(TOKEN_URLS[1], 400)

        with pytest.raises(HttpError) as error:
            api.fetch_usage()

        assert (error.value.code, error.value.url) == (400, TOKEN_URLS[1])
        assert USAGE_URL not in server.urls()
        assert read_credentials()["accessToken"] == "old-access"

    def test_refresh_fails_but_token_still_valid(self, api, server, credentials_file):
        expire_token(credentials_file, NOW + 60)
        server.add(TOKEN_URLS[0], 400)
        server.add(TOKEN_URLS[1], 400)
        server.add(USAGE_URL, USAGE)

        assert api.fetch_usage() == USAGE

        assert server.requests[-1].headers["Authorization"] == "Bearer old-access"

    def test_401_refreshes_and_retries_once(self, api, server, read_credentials):
        server.add(USAGE_URL, 401, USAGE)
        server.add(TOKEN_URLS[0], TOKEN)

        assert api.fetch_usage() == USAGE

        assert server.urls() == [USAGE_URL, TOKEN_URLS[0], USAGE_URL]
        assert server.requests[-1].headers["Authorization"] == "Bearer new-access"
        assert read_credentials()["accessToken"] == "new-access"

    def test_401_twice_raises(self, api, server):
        server.add(USAGE_URL, 401, 401)
        server.add(TOKEN_URLS[0], TOKEN)

        with pytest.raises(HttpError) as error:
            api.fetch_usage()

        assert error.value.code == 401
        assert server.urls() == [USAGE_URL, TOKEN_URLS[0], USAGE_URL]

    def test_401_and_forced_refresh_fails(self, api, server):
        server.add(USAGE_URL, 401)
        server.add(TOKEN_URLS[0], 400)
        server.add(TOKEN_URLS[1], 400)

        with pytest.raises(HttpError) as error:
            api.fetch_usage()

        assert (error.value.code, error.value.url) == (400, TOKEN_URLS[1])
        assert server.urls() == [USAGE_URL, TOKEN_URLS[0], TOKEN_URLS[1]]

    @pytest.mark.parametrize("code", [403, 429, 500])
    def test_other_errors_are_not_retried(self, api, server, code):
        server.add(USAGE_URL, code)

        with pytest.raises(HttpError) as error:
            api.fetch_usage()

        assert error.value.code == code
        assert server.urls() == [USAGE_URL]
