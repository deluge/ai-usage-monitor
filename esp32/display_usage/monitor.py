import time

from display_usage.api import CredentialsMissing, HttpError
from display_usage.utils import log
from display_usage.wifi import WifiError


# Retry wait times in seconds.
# After consecutive "Check token" (401/403) failures; the last one repeats.
AUTH_RETRY_DELAYS = (10, 20, 60)
API_ERROR_RETRY_DELAY = 60
NO_CREDENTIALS_RETRY_DELAY = 30
NETWORK_ERROR_RETRY_DELAY = 15
WIFI_ERROR_RETRY_DELAY = 15
WIFI_WAIT_DELAY = 1
LOADING_FRAME_DELAY = 0.5


class UsageMonitor:
    """Single-threaded version of the Pi's UsageMonitor: one loop fetches and draws."""

    def __init__(self, api, oled, wifi, api_request_interval=120, display_refresh_interval=30):
        self.api = api
        self.oled = oled
        self.wifi = wifi
        self.api_request_interval = api_request_interval
        self.display_refresh_interval = display_refresh_interval
        self.usage = None
        self.error = None
        self.fatal = False
        self.auth_failures = 0

    def fetch_once(self):
        """Fetch usage once and return how many seconds to wait before the next fetch."""
        try:
            if not self.wifi.connect():
                return WIFI_WAIT_DELAY
            self.wifi.sync_clock()
            usage = self.api.fetch_usage()
        except HttpError as error:
            return self.handle_http_error(error)
        except CredentialsMissing:
            return self.handle_missing_credentials()
        except WifiError as error:
            return self.handle_wifi_error(error)
        except Exception as error:  # DNS, timeout, NTP, ...
            return self.handle_network_error(error)

        self.auth_failures = 0
        self.usage, self.error = usage, None
        return self.api_request_interval

    def handle_http_error(self, error):
        log(f"HTTP {error.code} from {error.url}: {error.body}")
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

    def handle_missing_credentials(self):
        self.show_fatal_error("No credentials", self.api.credentials_file)
        return NO_CREDENTIALS_RETRY_DELAY

    def handle_wifi_error(self, error):
        log(f"Wi-Fi {self.wifi.ssid}: {error}")
        self.show_fatal_error("Wi-Fi error", self.wifi.ssid, str(error))
        return WIFI_ERROR_RETRY_DELAY

    def handle_network_error(self, error):
        log(f"Network error: {error}")
        if self.usage is None:
            self.error = ("No network?", str(error))
        return NETWORK_ERROR_RETRY_DELAY

    def show_fatal_error(self, *lines):
        self.error = lines
        self.fatal = True

    def render_usage(self):
        if self.usage is not None:
            self.oled.show_usage(self.usage)
        elif self.error:
            self.oled.show_message(*self.error)
        else:
            self.oled.show_loading()

    def run(self):
        dots = 1
        next_fetch = next_render = time.ticks_ms()
        while True:
            now = time.ticks_ms()
            if time.ticks_diff(now, next_fetch) >= 0:
                delay = self.fetch_once()
                next_fetch = time.ticks_add(time.ticks_ms(), int(delay * 1000))
                next_render = now  # show the new data or error right away
            if self.usage is None and not self.fatal:
                self.oled.show_loading(dots)
                dots = dots % 3 + 1
            elif time.ticks_diff(now, next_render) >= 0:
                self.render_usage()
                next_render = time.ticks_add(now, self.display_refresh_interval * 1000)
            time.sleep(LOADING_FRAME_DELAY)
