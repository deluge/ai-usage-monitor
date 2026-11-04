"""
Access to the Claude usage data.

Credentials file: ~/.usage-monitor/credentials.json
  {"claudeAiOauth": {"accessToken": "...", "refreshToken": "...",
                     "expiresAt": 1234567890000}}

Note: /api/oauth/usage is an undocumented endpoint (the one Claude Code itself
uses for /usage). Anthropic may change or remove it at any time.
"""

import json
import os
import time
import urllib.error
import urllib.request

from display_usage.utils import log, read_error_body


CREDENTIALS_FILE = os.path.expanduser("~/.usage-monitor/credentials.json")
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
TOKEN_URLS = [
    "https://platform.claude.com/v1/oauth/token",
    "https://console.anthropic.com/v1/oauth/token",
]
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
USER_AGENT = "claude-code/2.0.0"
TOKEN_REFRESH_BUFFER = 300  # refresh the token 5 minutes before it expires


class ClaudeApi:
    def __init__(self, credentials_file=CREDENTIALS_FILE, timeout=20):
        self.credentials_file = os.path.expanduser(credentials_file)
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
        if oauth.get("expiresAt", 0) / 1000 < time.time() + TOKEN_REFRESH_BUFFER:
            try:
                self.refresh_token(credentials)
            except urllib.error.HTTPError:
                pass  # already logged; try the old token anyway
        return oauth["accessToken"]

    def refresh_token(self, credentials):
        oauth = credentials["claudeAiOauth"]
        token_response = self.request_new_token(oauth["refreshToken"])
        oauth["accessToken"] = token_response["access_token"]
        if token_response.get("refresh_token"):
            oauth["refreshToken"] = token_response["refresh_token"]
        expires_in = token_response.get("expires_in", 3600)
        oauth["expiresAt"] = int((time.time() + expires_in) * 1000)
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
            except urllib.error.HTTPError as error:
                log(f"Token refresh at {url}: HTTP {error.code} {read_error_body(error, 300)}")
                last_error = error
        raise last_error

    def request_json(self, url, headers=None, body=None):
        """GET the url, or POST the body if one is given, and return the JSON response."""
        request = urllib.request.Request(
            url,
            data=None if body is None else json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
                **(headers or {}),
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.load(response)

    def read_credentials(self):
        with open(self.credentials_file) as credentials_handle:
            return json.load(credentials_handle)

    def write_credentials(self, data):
        temporary_path = self.credentials_file + ".tmp"
        with open(temporary_path, "w") as temporary_handle:
            json.dump(data, temporary_handle, indent=2)
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, self.credentials_file)
