import time

import network
import ntptime

from display_usage.errors import WifiError
from display_usage.utils import log


CLOCK_SYNC_INTERVAL = 6 * 3600 * 1000  # milliseconds; the ESP32's clock drifts
WIFI_ERRORS = {
    network.STAT_WRONG_PASSWORD: "Wrong password",
    network.STAT_NO_AP_FOUND: "Not found",
}


class Wifi:
    def __init__(self, ssid, password, hostname="usage-monitor", tx_power=None):
        self.ssid = ssid
        self.password = password
        network.hostname(hostname)
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        if tx_power is not None:
            self.wlan.config(txpower=tx_power)
        self.last_clock_sync = None

    def connect(self):
        """Start connecting if needed and return True once connected and the clock is set.

        Raises WifiError if the last attempt failed for a known reason.
        """
        if self.wlan.isconnected():
            self.sync_clock()
            return True
        status = self.wlan.status()
        if status == network.STAT_CONNECTING:
            return False
        log(f"Connecting to Wi-Fi {self.ssid}")
        try:
            self.wlan.connect(self.ssid, self.password)
        except OSError as error:  # the Wi-Fi driver is still busy
            log(f"Wi-Fi: {error}")
        if status in WIFI_ERRORS:
            raise WifiError(WIFI_ERRORS[status])
        return False

    def sync_clock(self):
        """Set the clock from the internet on first use and then every few hours."""
        if (
            self.last_clock_sync is not None
            and time.ticks_diff(time.ticks_ms(), self.last_clock_sync) < CLOCK_SYNC_INTERVAL
        ):
            return
        ntptime.settime()
        self.last_clock_sync = time.ticks_ms()
        log("Clock synced.")
