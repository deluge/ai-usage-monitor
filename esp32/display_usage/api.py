"""
Access to the Claude usage data (MicroPython version for the ESP32).

Credentials file: /credentials.json on the ESP32's flash
  {"claudeAiOauth": {"accessToken": "...", "refreshToken": "...",
                     "expiresAt": 1234567890000}}

Note: /api/oauth/usage is an undocumented endpoint (the one Claude Code itself
uses for /usage). Anthropic may change or remove it at any time.
"""

import gc
import json
import os

import requests

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


class HttpError(Exception):
    def __init__(self, code, url, body):
        super().__init__(f"HTTP {code}")
        self.code = code
        self.url = url
        self.body = body


class CredentialsMissing(Exception):
    pass


class ClaudeApi:
    def __init__(self, credentials_file=CREDENTIALS_FILE, timeout=20):
        self.credentials_file = credentials_file
        self.timeout = timeout

    def fetch_usage(self):
        headers = {
            "Authorization": f"Bearer {self.get_token()}",
            "anthropic-beta": "oauth-2025-04-20",
        }
        return self.request_json(USAGE_URL, headers=headers)

    def get_token(self):
        credentials = self.read_credentials()
        oauth = credentials["claudeAiOauth"]
        # Integer math only: MicroPython floats are too imprecise for timestamps.
        if oauth.get("expiresAt", 0) // 1000 < unix_time() + TOKEN_REFRESH_BUFFER:
            try:
                self.refresh_token(credentials)
            except HttpError:
                pass  # already logged; try the old token anyway
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
        """Try each token URL in turn and raise the last error if all of them fail."""
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
        raise last_error

    def request_json(self, url, headers=None, body=None):
        """GET the url, or POST the body if one is given, and return the JSON response."""
        all_headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
        all_headers.update(headers or {})
        gc.collect()  # TLS needs a large block of free memory
        response = requests.request(
            "GET" if body is None else "POST",
            url,
            data=None if body is None else json.dumps(body),
            headers=all_headers,
            timeout=self.timeout,
        )
        try:
            if response.status_code >= 400:
                raise HttpError(response.status_code, url, response.text[:500])
            return response.json()
        finally:
            response.close()

    def read_credentials(self):
        try:
            with open(self.credentials_file) as credentials_handle:
                return json.load(credentials_handle)
        except OSError:
            raise CredentialsMissing(self.credentials_file)

    def write_credentials(self, data):
        temporary_path = self.credentials_file + ".tmp"
        with open(temporary_path, "w") as temporary_handle:
            json.dump(data, temporary_handle)
        os.rename(temporary_path, self.credentials_file)
