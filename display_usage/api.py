"""
Access to the Claude usage data.

Credentials file: credentials.json in the project folder (Pi) or on the board (ESP32)
  {"claudeAiOauth": {"accessToken": "...", "refreshToken": "...",
                     "expiresAt": 1234567890000}}

Note: /api/oauth/usage is an undocumented endpoint (the one Claude Code itself
uses for /usage). Anthropic may change or remove it at any time.
"""

import gc
import json
import os

import requests

from display_usage.errors import CredentialsMissing, HttpError
from display_usage.utils import log, unix_time


CREDENTIALS_FILE = "credentials.json"
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
TOKEN_URLS = [
    "https://platform.claude.com/v1/oauth/token",
    "https://console.anthropic.com/v1/oauth/token",
]
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
USER_AGENT = "claude-code/2.0.0"
TOKEN_REFRESH_BUFFER = 300  # refresh the token 5 minutes before it expires


def expand_user(path):
    try:
        from os.path import expanduser
    except ImportError:
        return path
    return expanduser(path)


class ClaudeApi:
    def __init__(self, credentials_file=CREDENTIALS_FILE, timeout=20):
        self.credentials_file = credentials_file
        self.credentials_path = expand_user(credentials_file)
        self.timeout = timeout

    def fetch_usage(self):
        try:
            return self.request_usage(self.get_token())
        except HttpError as error:
            if error.code != 401:
                raise
        # The token was rejected before its expiry time (e.g. revoked because
        # another client refreshed it): get a new one and try exactly once more.
        log("Usage request returned HTTP 401, refreshing the token and retrying once.")
        return self.request_usage(self.get_token(force_refresh=True))

    def request_usage(self, token):
        headers = {
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
        }
        return self.request_json(USAGE_URL, headers=headers)

    def get_token(self, force_refresh=False):
        """Return a usable access token, refreshing it if needed.

        Raises the HttpError of a failed refresh unless the old token is still
        valid, so that a broken login is not hammered with doomed requests.
        """
        credentials = self.read_credentials()
        oauth = credentials["claudeAiOauth"]
        expires_at = oauth.get("expiresAt", 0) // 1000
        if force_refresh or expires_at < unix_time() + TOKEN_REFRESH_BUFFER:
            try:
                self.refresh_token(credentials)
            except HttpError:
                if force_refresh or expires_at <= unix_time():
                    raise
                # Still valid for a few minutes: use it, refresh again next time.
        return oauth["accessToken"]

    def refresh_token(self, credentials):
        oauth = credentials["claudeAiOauth"]
        token_response = self.request_new_token(oauth["refreshToken"])
        oauth["accessToken"] = token_response["access_token"]
        if token_response.get("refresh_token"):
            oauth["refreshToken"] = token_response["refresh_token"]
        expires_in = int(token_response.get("expires_in", 3600))
        oauth["expiresAt"] = (unix_time() + expires_in) * 1000
        self.write_credentials(credentials)
        log("Token refreshed.")

    def request_new_token(self, refresh_token):
        """Try each token URL in turn and raise the last error if all of them fail.

        The endpoints do not behave the same: one may reject a refresh token
        (e.g. with HTTP 400) that the other one accepts, so always try the next
        URL. Only a rate limit (429) stops early, as more requests won't help.
        """
        body = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
        }
        last_error = None
        for url in TOKEN_URLS:
            try:
                return self.request_json(url, body=body)
            except HttpError as error:
                log(f"Token refresh at {url}: HTTP {error.code} {error.body[:300]}")
                last_error = error
                if error.code == 429:
                    break
        raise last_error

    def request_json(self, url, headers=None, body=None):
        """GET the url, or POST the body if one is given, and return the JSON response."""
        all_headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
        all_headers.update(headers or {})
        gc.collect()  # the ESP32 needs a large block of free memory for TLS
        response = requests.request(
            "GET" if body is None else "POST",
            url,
            data=None if body is None else json.dumps(body),
            headers=all_headers,
            timeout=self.timeout,
        )
        try:
            if response.status_code >= 400:
                raise HttpError(
                    response.status_code, url, response.text[:500], response.headers
                )
            return response.json()
        finally:
            response.close()

    def read_credentials(self):
        try:
            with open(self.credentials_path) as credentials_handle:
                return json.load(credentials_handle)
        except OSError:
            raise CredentialsMissing(self.credentials_file)

    def write_credentials(self, data):
        temporary_path = self.credentials_path + ".tmp"
        with open(temporary_path, "w") as temporary_handle:
            json.dump(data, temporary_handle)
        if hasattr(os, "chmod"):
            os.chmod(temporary_path, 0o600)
        os.rename(temporary_path, self.credentials_path)
