import datetime
import email.utils
import os
import threading
import time
import urllib.error

from display_usage.api import TOKEN_URLS
from display_usage.utils import log, read_error_body


# Retry wait times in seconds.
# After consecutive auth failures (401/403, or a rejected token refresh);
# the last one repeats. Each retry can cost up to three requests (usage, token
# refresh, usage again), so back off far enough to stay clear of rate limits.
AUTH_RETRY_DELAYS = (10, 30, 120, 600)
# Show "Check token" on the display from this many consecutive auth failures on.
AUTH_FAILURES_BEFORE_MESSAGE = 3
API_ERROR_RETRY_DELAY = 60
# After consecutive 429 (rate limit) responses without a usable Retry-After header:
# start at this delay and double it each time, up to the maximum.
RATE_LIMIT_BASE_DELAY = 120
RATE_LIMIT_MAX_DELAY = 900
NO_CREDENTIALS_RETRY_DELAY = 30
NETWORK_ERROR_RETRY_DELAY = 15
# Network errors and rate limits keep the last usage on the display. Once it is
# older than this (in seconds, or 3 request intervals if that is longer), the
# display says when it is from.
STALE_AFTER = 600


class UsageMonitor:
    def __init__(self, api, oled, api_request_interval=120, display_refresh_interval=30):
        self.api = api
        self.oled = oled
        self.api_request_interval = api_request_interval
        self.display_refresh_interval = display_refresh_interval
        self.state = {"usage": None, "error": None, "fatal": False, "updated_at": None}
        self.lock = threading.Lock()
        self.auth_failures = 0
        self.rate_limit_failures = 0

    def fetch_loop(self):
        while True:
            time.sleep(self.fetch_once())

    def fetch_once(self):
        """Fetch usage once and return how many seconds to wait before the next fetch."""
        try:
            usage = self.api.fetch_usage()
        except urllib.error.HTTPError as error:
            return self.handle_http_error(error)
        except FileNotFoundError:
            return self.handle_missing_credentials()
        except Exception as error:  # no Wi-Fi yet, timeout, ...
            return self.handle_network_error(error)

        self.auth_failures = 0
        self.rate_limit_failures = 0
        with self.lock:
            self.state["usage"], self.state["error"] = usage, None
            self.state["updated_at"] = time.time()
        return self.api_request_interval

    def handle_http_error(self, error):
        log(f"HTTP {error.code} from {error.url}: {read_error_body(error)}")
        if error.code == 429:
            return self.handle_rate_limit(error)
        if not self.is_auth_error(error):
            self.show_fatal_error("API error", f"HTTP {error.code}", "")
            return API_ERROR_RETRY_DELAY

        delay = AUTH_RETRY_DELAYS[min(self.auth_failures, len(AUTH_RETRY_DELAYS) - 1)]
        self.auth_failures += 1
        log(f"Auth failure #{self.auth_failures}, retrying in {delay}s")
        # Keep the loading screen up while the early retries are pending.
        if self.auth_failures >= AUTH_FAILURES_BEFORE_MESSAGE:
            self.show_fatal_error("API error", f"HTTP {error.code}", "Check token")
        return delay

    @staticmethod
    def is_auth_error(error):
        """401/403 anywhere, or 400 from the token endpoint (refresh token rejected)."""
        return error.code in (401, 403) or (error.code == 400 and error.url in TOKEN_URLS)

    def handle_rate_limit(self, error):
        """Wait as long as the server asks, or back off exponentially.

        The last known usage stays on the display; the message is only shown
        if no usage has been fetched yet.
        """
        delay = self.parse_retry_after(error.headers.get("Retry-After"))
        if delay is None:
            delay = min(
                RATE_LIMIT_BASE_DELAY * 2**self.rate_limit_failures, RATE_LIMIT_MAX_DELAY
            )
        self.rate_limit_failures += 1
        log(f"Rate limited (#{self.rate_limit_failures}), retrying in {delay}s")
        with self.lock:
            if self.state["usage"] is None:
                self.state["error"] = ("Rate limited", f"Retry in {(delay + 59) // 60} min", "")
                self.state["fatal"] = True  # leave the loading screen
        return delay

    @staticmethod
    def parse_retry_after(value):
        """Return the Retry-After header (seconds or HTTP date) in seconds, or None."""
        if not value:
            return None
        value = value.strip()
        if value.isdigit():
            seconds = int(value)
        else:
            try:
                seconds = int(
                    email.utils.parsedate_to_datetime(value).timestamp() - time.time()
                )
            except (TypeError, ValueError):
                return None
        return min(max(seconds, NETWORK_ERROR_RETRY_DELAY), RATE_LIMIT_MAX_DELAY)

    def handle_missing_credentials(self):
        directory, filename = os.path.split(self.api.credentials_file)
        directory = directory.replace(os.path.expanduser("~"), "~", 1) + "/"
        self.show_fatal_error("No credentials", directory, filename)
        return NO_CREDENTIALS_RETRY_DELAY

    def handle_network_error(self, error):
        log(f"Network error: {error}")
        with self.lock:
            if self.state["usage"] is None:
                self.state["error"] = ("No network?", str(error)[:20])
        return NETWORK_ERROR_RETRY_DELAY

    def show_fatal_error(self, *lines):
        with self.lock:
            self.state["error"] = lines
            self.state["fatal"] = True

    def render_usage(self):
        with self.lock:
            usage, error = self.state["usage"], self.state["error"]
            updated_at = self.state["updated_at"]
        # While usage is known, an error is only set by an auth or API error
        # (rate limits and network errors keep it unset); show it instead of
        # silently freezing on old numbers. The next successful fetch clears it.
        if error:
            self.oled.show_message(*error)
        elif usage is not None:
            stale_after = max(STALE_AFTER, 3 * self.api_request_interval)
            if time.time() - updated_at > stale_after:
                self.oled.show_usage(usage, datetime.datetime.fromtimestamp(updated_at))
            else:
                self.oled.show_usage(usage)
        else:
            self.oled.show_loading()

    def loading_screen(self):
        dots = 1
        while True:
            with self.lock:
                if self.state["usage"] is not None or self.state["fatal"]:
                    return
            self.oled.show_loading(dots)
            dots = dots % 3 + 1
            time.sleep(0.5)

    def run(self):
        threading.Thread(target=self.fetch_loop, daemon=True).start()
        self.loading_screen()
        while True:
            self.render_usage()
            time.sleep(self.display_refresh_interval)
