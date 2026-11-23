import email.utils
import os
import threading
import time
import urllib.error

from display_usage.utils import log, read_error_body


# Retry wait times in seconds.
# After consecutive "Check token" (401/403) failures; the last one repeats.
AUTH_RETRY_DELAYS = (10, 20, 60)
API_ERROR_RETRY_DELAY = 60
RATE_LIMIT_BASE_DELAY = 120
RATE_LIMIT_MAX_DELAY = 900
NO_CREDENTIALS_RETRY_DELAY = 30
NETWORK_ERROR_RETRY_DELAY = 15


class UsageMonitor:
    def __init__(self, api, oled, api_request_interval=120, display_refresh_interval=30):
        self.api = api
        self.oled = oled
        self.api_request_interval = api_request_interval
        self.display_refresh_interval = display_refresh_interval
        self.state = {"usage": None, "error": None, "fatal": False}
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
        return self.api_request_interval

    def handle_http_error(self, error):
        log(f"HTTP {error.code} from {error.url}: {read_error_body(error)}")
        if error.code == 429:
            return self.handle_rate_limit(error)
        if error.code not in (401, 403):
            self.show_fatal_error("API error", f"HTTP {error.code}", "")
            return API_ERROR_RETRY_DELAY

        delay = AUTH_RETRY_DELAYS[min(self.auth_failures, len(AUTH_RETRY_DELAYS) - 1)]
        self.auth_failures += 1
        log(f"Auth failure #{self.auth_failures}, retrying in {delay}s")
        # Keep the loading screen up while the early retries are pending.
        if self.auth_failures >= len(AUTH_RETRY_DELAYS):
            self.show_fatal_error("API error", f"HTTP {error.code}", "Check token")
        return delay

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
        if usage is not None:
            self.oled.show_usage(usage)
        elif error:
            self.oled.show_message(*error)
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
