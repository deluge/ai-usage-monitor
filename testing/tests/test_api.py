import json
import os
import stat
import urllib.error

import pytest
from freezegun import freeze_time

from conftest import NOW
from display_usage.api import CLIENT_ID, TOKEN_URLS, USAGE_URL, USER_AGENT, ClaudeApi


USAGE = {"five_hour": {"utilization": 12.0}, "seven_day": {"utilization": 34.0}}
TOKEN = {"access_token": "new-access", "refresh_token": "new-refresh", "expires_in": 7200}


def expire_token(credentials_file, expires_at=NOW):
    data = json.loads(credentials_file.read_text())
    data["claudeAiOauth"]["expiresAt"] = expires_at * 1000
    credentials_file.write_text(json.dumps(data))


def test_default_credentials_file():
    assert ClaudeApi().credentials_file == os.path.expanduser(
        "~/.usage-monitor/credentials.json"
    )


def test_credentials_file_expands_home():
    assert ClaudeApi("~/creds.json").credentials_file == os.path.expanduser("~/creds.json")


def test_missing_credentials_file(tmp_path, server):
    api = ClaudeApi(credentials_file=str(tmp_path / "missing.json"))

    with pytest.raises(FileNotFoundError):
        api.fetch_usage()

    assert server.requests == []


@freeze_time("2026-11-24 12:00:00")
class TestFetchUsage:
    def test_valid_token(self, api, server):
        server.add(USAGE_URL, USAGE)

        assert api.fetch_usage() == USAGE

        request = server.requests[0]
        assert request.get_header("Authorization") == "Bearer old-access"
        assert request.get_header("Anthropic-beta") == "oauth-2025-04-20"
        assert request.get_header("User-agent") == USER_AGENT
        assert request.data is None

    def test_refreshes_expiring_token(self, api, server, credentials_file, read_credentials):
        expire_token(credentials_file, NOW + 60)
        server.add(TOKEN_URLS[0], TOKEN)
        server.add(USAGE_URL, USAGE)

        assert api.fetch_usage() == USAGE

        assert server.urls() == [TOKEN_URLS[0], USAGE_URL]
        assert json.loads(server.requests[0].data) == {
            "grant_type": "refresh_token",
            "refresh_token": "old-refresh",
            "client_id": CLIENT_ID,
        }
        assert server.requests[1].get_header("Authorization") == "Bearer new-access"
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

        with pytest.raises(urllib.error.HTTPError) as error:
            api.fetch_usage()

        assert error.value.code == 429
        assert server.urls() == [TOKEN_URLS[0]]

    def test_refresh_fails_everywhere_with_expired_token(
        self, api, server, credentials_file, read_credentials
    ):
        expire_token(credentials_file)
        server.add(TOKEN_URLS[0], 400)
        server.add(TOKEN_URLS[1], 400)

        with pytest.raises(urllib.error.HTTPError) as error:
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

        assert server.requests[-1].get_header("Authorization") == "Bearer old-access"

    def test_401_refreshes_and_retries_once(self, api, server, read_credentials):
        server.add(USAGE_URL, 401, USAGE)
        server.add(TOKEN_URLS[0], TOKEN)

        assert api.fetch_usage() == USAGE

        assert server.urls() == [USAGE_URL, TOKEN_URLS[0], USAGE_URL]
        assert server.requests[-1].get_header("Authorization") == "Bearer new-access"
        assert read_credentials()["accessToken"] == "new-access"

    def test_401_twice_raises(self, api, server):
        server.add(USAGE_URL, 401, 401)
        server.add(TOKEN_URLS[0], TOKEN)

        with pytest.raises(urllib.error.HTTPError) as error:
            api.fetch_usage()

        assert error.value.code == 401
        assert server.urls() == [USAGE_URL, TOKEN_URLS[0], USAGE_URL]

    def test_401_and_forced_refresh_fails(self, api, server):
        server.add(USAGE_URL, 401)
        server.add(TOKEN_URLS[0], 400)
        server.add(TOKEN_URLS[1], 400)

        with pytest.raises(urllib.error.HTTPError) as error:
            api.fetch_usage()

        assert (error.value.code, error.value.url) == (400, TOKEN_URLS[1])
        assert server.urls() == [USAGE_URL, TOKEN_URLS[0], TOKEN_URLS[1]]

    @pytest.mark.parametrize("code", [403, 429, 500])
    def test_other_errors_are_not_retried(self, api, server, code):
        server.add(USAGE_URL, code)

        with pytest.raises(urllib.error.HTTPError) as error:
            api.fetch_usage()

        assert error.value.code == code
        assert server.urls() == [USAGE_URL]
