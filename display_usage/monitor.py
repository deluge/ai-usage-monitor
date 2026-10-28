import os
import threading
import time
import urllib.error

from display_usage.utils import log


class UsageMonitor:
    def __init__(self, api, oled, api_request_interval=120, display_refresh_interval=30):
        self.api = api
        self.oled = oled
        self.api_request_interval = api_request_interval
        self.display_refresh_interval = display_refresh_interval
        self.state = {"usage": None, "error": None, "fatal": False}
        self.lock = threading.Lock()

    def fetch_loop(self):
        while True:
            try:
                usage = self.api.fetch_usage()
                with self.lock:
                    self.state["usage"], self.state["error"] = usage, None
                time.sleep(self.api_request_interval)
            except urllib.error.HTTPError as error:
                try:
                    body = error.read().decode(errors="replace")[:500]
                except Exception:
                    body = ""
                log(f"HTTP {error.code} from {error.url}: {body}")
                hint = "Check token" if error.code in (401, 403) else ""
                with self.lock:
                    self.state["error"] = ("API error", f"HTTP {error.code}", hint)
                    self.state["fatal"] = True
                time.sleep(60)
            except FileNotFoundError:
                directory, filename = os.path.split(self.api.credentials_file)
                with self.lock:
                    self.state["error"] = (
                        "No credentials",
                        directory.replace(os.path.expanduser("~"), "~", 1) + "/",
                        filename,
                    )
                    self.state["fatal"] = True
                time.sleep(30)
            except Exception as error:  # no Wi-Fi yet, timeout, ...
                log(f"Network error: {error}")
                with self.lock:
                    if self.state["usage"] is None:
                        self.state["error"] = ("No network?", str(error)[:20])
                time.sleep(15)

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
