import time

from display_usage.api import TOKEN_URLS
from display_usage.errors import CredentialsMissing, HttpError, WifiError
from display_usage.utils import log


try:
    from email.utils import parsedate_to_datetime
except ImportError:  # MicroPython: Retry-After only works in seconds there
    parsedate_to_datetime = None


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
WIFI_ERROR_RETRY_DELAY = 15
WIFI_WAIT_DELAY = 1
FRAME_DELAY = 0.5  # speed of the loading animation


class UsageMonitor:
    def __init__(
        self, api, oled, wifi=None, api_request_interval=120, display_refresh_interval=30
    ):
        self.api = api
        self.oled = oled
        self.wifi = wifi
        self.api_request_interval = api_request_interval
        self.display_refresh_interval = display_refresh_interval
        self.usage = None
        self.error = None
        self.fatal = False
        self.auth_failures = 0
        self.rate_limit_failures = 0

    def fetch_once(self):
        """Fetch usage once and return how many seconds to wait before the next fetch."""
        try:
            if self.wifi and not self.wifi.connect():
                return WIFI_WAIT_DELAY
            usage = self.api.fetch_usage()
        except HttpError as error:
            return self.handle_http_error(error)
        except CredentialsMissing:
            return self.handle_missing_credentials()
        except WifiError as error:
            return self.handle_wifi_error(error)
        except Exception as error:  # no network yet, timeout, ...
            return self.handle_network_error(error)

        self.auth_failures = 0
        self.rate_limit_failures = 0
        self.usage, self.error = usage, None
        return self.api_request_interval

    def handle_http_error(self, error):
        log(f"HTTP {error.code} from {error.url}: {error.body}")
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
        delay = self.parse_retry_after(error.headers.get("retry-after"))
        if delay is None:
            delay = min(
                RATE_LIMIT_BASE_DELAY * 2**self.rate_limit_failures, RATE_LIMIT_MAX_DELAY
            )
        self.rate_limit_failures += 1
        log(f"Rate limited (#{self.rate_limit_failures}), retrying in {delay}s")
        if self.usage is None:
            self.error = ("Rate limited", f"Retry in {(delay + 59) // 60} min", "")
            self.fatal = True  # leave the loading screen
        return delay

    @staticmethod
    def parse_retry_after(value):
        """Return the Retry-After header (seconds or HTTP date) in seconds, or None."""
        if not value:
            return None
        value = value.strip()
        if value.isdigit():
            seconds = int(value)
        elif parsedate_to_datetime is None:
            return None
        else:
            try:
                seconds = int(parsedate_to_datetime(value).timestamp() - time.time())
            except (TypeError, ValueError):
                return None
        return min(max(seconds, NETWORK_ERROR_RETRY_DELAY), RATE_LIMIT_MAX_DELAY)

    def handle_missing_credentials(self):
        directory, _, filename = self.api.credentials_file.rpartition("/")
        self.show_fatal_error("No credentials", directory + "/" if directory else "", filename)
        return NO_CREDENTIALS_RETRY_DELAY

    def handle_wifi_error(self, error):
        log(f"Wi-Fi {self.wifi.ssid}: {error}")
        self.show_fatal_error("Wi-Fi error", self.wifi.ssid, str(error))
        return WIFI_ERROR_RETRY_DELAY

    def handle_network_error(self, error):
        log(f"Network error: {error}")
        if self.usage is None:
            self.error = ("No network?", str(error)[:20])
        return NETWORK_ERROR_RETRY_DELAY

    def show_fatal_error(self, *lines):
        self.error = lines
        self.fatal = True

    def render_usage(self):
        # While usage is known, an error is only set by an auth, API or Wi-Fi
        # error (rate limits and network errors keep it unset); show it instead
        # of silently freezing on old numbers. The next successful fetch clears it.
        if self.error:
            self.oled.show_message(*self.error)
        elif self.usage is not None:
            self.oled.show_usage(self.usage)
        else:
            self.oled.show_loading()

    def run(self):
        dots = 1
        fetch_in = render_in = 0  # seconds until the next fetch / redraw
        while True:
            if fetch_in <= 0:
                fetch_in = self.fetch_once()
                render_in = 0  # show the new data or error right away
            if self.usage is None and not self.fatal:
                self.oled.show_loading(dots)
                dots = dots % 3 + 1
            elif render_in <= 0:
                self.render_usage()
                render_in = self.display_refresh_interval
            time.sleep(FRAME_DELAY)
            fetch_in -= FRAME_DELAY
            render_in -= FRAME_DELAY
