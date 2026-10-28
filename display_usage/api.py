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

from display_usage.utils import log


CREDENTIALS_FILE = os.path.expanduser("~/.usage-monitor/credentials.json")
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
TOKEN_URLS = [
    "https://platform.claude.com/v1/oauth/token",
    "https://console.anthropic.com/v1/oauth/token",
]
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
USER_AGENT = "claude-code/2.0.0"


class ClaudeApi:
    def __init__(self, credentials_file=CREDENTIALS_FILE, timeout=20):
        self.credentials_file = os.path.expanduser(credentials_file)
        self.timeout = timeout

    def read_credentials(self):
        with open(self.credentials_file) as credentials_handle:
            return json.load(credentials_handle)

    def write_credentials(self, data):
        temporary_path = self.credentials_file + ".tmp"
        with open(temporary_path, "w") as temporary_handle:
            json.dump(data, temporary_handle, indent=2)
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, self.credentials_file)

    def refresh_token(self, credentials):
        oauth = credentials["claudeAiOauth"]
        body = json.dumps(
            {
                "grant_type": "refresh_token",
                "refresh_token": oauth["refreshToken"],
                "client_id": CLIENT_ID,
            }
        ).encode()
        last_error = None
        for url in TOKEN_URLS:
            request = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    token_response = json.load(response)
                break
            except urllib.error.HTTPError as error:
                detail = error.read().decode(errors="replace")[:300]
                log(f"Token refresh at {url}: HTTP {error.code} {detail}")
                last_error = error
        else:
            raise last_error
        oauth["accessToken"] = token_response["access_token"]
        if token_response.get("refresh_token"):
            oauth["refreshToken"] = token_response["refresh_token"]
        oauth["expiresAt"] = int((time.time() + token_response.get("expires_in", 3600)) * 1000)
        self.write_credentials(credentials)
        log("Token refreshed.")

    def get_token(self):
        credentials = self.read_credentials()
        oauth = credentials["claudeAiOauth"]
        if oauth.get("expiresAt", 0) / 1000 < time.time() + 300:  # 5 min buffer
            try:
                self.refresh_token(credentials)
            except urllib.error.HTTPError:
                pass
        return oauth["accessToken"]

    def fetch_usage(self):
        request = urllib.request.Request(
            USAGE_URL,
            headers={
                "Authorization": f"Bearer {self.get_token()}",
                "anthropic-beta": "oauth-2025-04-20",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.load(response)
