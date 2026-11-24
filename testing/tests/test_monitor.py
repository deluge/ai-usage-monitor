import pytest
from freezegun import freeze_time

from display_usage import monitor as monitor_module
from display_usage.api import TOKEN_URLS, USAGE_URL
from display_usage.monitor import (
    API_ERROR_RETRY_DELAY,
    AUTH_RETRY_DELAYS,
    NETWORK_ERROR_RETRY_DELAY,
    NO_CREDENTIALS_RETRY_DELAY,
    RATE_LIMIT_MAX_DELAY,
    UsageMonitor,
)
from testing.fakes.api import FakeApi, http_error


USAGE = {"five_hour": {"utilization": 12.0}, "seven_day": {"utilization": 34.0}}


class StopLoop(Exception):
    pass


def make_monitor(display, *results):
    return UsageMonitor(FakeApi(*results), display)


def test_success(display):
    monitor = make_monitor(display, USAGE)

    assert monitor.fetch_once() == monitor.api_request_interval
    assert monitor.state == {"usage": USAGE, "error": None, "fatal": False}


def test_success_resets_failures_and_clears_error(display):
    monitor = make_monitor(display, http_error(USAGE_URL, 500), USAGE)
    monitor.auth_failures = monitor.rate_limit_failures = 2

    monitor.fetch_once()
    assert monitor.state["error"] is not None

    monitor.fetch_once()
    assert monitor.state["error"] is None
    assert (monitor.auth_failures, monitor.rate_limit_failures) == (0, 0)


class TestAuthErrors:
    def test_retry_delays(self, display):
        errors = [http_error(USAGE_URL, 401) for _ in range(len(AUTH_RETRY_DELAYS) + 2)]
        monitor = make_monitor(display, *errors)

        delays = [monitor.fetch_once() for _ in errors]

        assert delays == [*AUTH_RETRY_DELAYS, AUTH_RETRY_DELAYS[-1], AUTH_RETRY_DELAYS[-1]]

    def test_message_only_after_repeated_failures(self, display):
        monitor = make_monitor(display, *[http_error(USAGE_URL, 403) for _ in range(3)])

        monitor.fetch_once()
        monitor.fetch_once()
        assert monitor.state == {"usage": None, "error": None, "fatal": False}

        monitor.fetch_once()
        assert monitor.state["error"] == ("API error", "HTTP 403", "Check token")
        assert monitor.state["fatal"] is True

    @pytest.mark.parametrize(
        "url, code, expected",
        [
            (USAGE_URL, 401, True),
            (USAGE_URL, 403, True),
            (TOKEN_URLS[0], 401, True),
            (TOKEN_URLS[1], 400, True),
            (USAGE_URL, 400, False),
            (USAGE_URL, 500, False),
        ],
    )
    def test_is_auth_error(self, url, code, expected):
        assert UsageMonitor.is_auth_error(http_error(url, code)) is expected


def test_api_error(display):
    monitor = make_monitor(display, http_error(USAGE_URL, 500))

    assert monitor.fetch_once() == API_ERROR_RETRY_DELAY
    assert monitor.state["error"] == ("API error", "HTTP 500", "")
    assert monitor.state["fatal"] is True


class TestRateLimit:
    def test_retry_after_seconds(self, display):
        monitor = make_monitor(
            display, http_error(USAGE_URL, 429, headers={"Retry-After": "90"})
        )

        assert monitor.fetch_once() == 90
        assert monitor.state["error"] == ("Rate limited", "Retry in 2 min", "")
        assert monitor.state["fatal"] is True

    def test_exponential_backoff(self, display):
        errors = [http_error(USAGE_URL, 429) for _ in range(5)]
        monitor = make_monitor(display, *errors)

        assert [monitor.fetch_once() for _ in errors] == [120, 240, 480, 900, 900]

    def test_keeps_known_usage(self, display):
        monitor = make_monitor(display, USAGE, http_error(USAGE_URL, 429))
        monitor.fetch_once()

        monitor.fetch_once()

        assert monitor.state == {"usage": USAGE, "error": None, "fatal": False}


@freeze_time("2026-11-24 12:00:00")
class TestParseRetryAfter:
    @pytest.mark.parametrize("value", [None, "", "soon"])
    def test_unusable(self, value):
        assert UsageMonitor.parse_retry_after(value) is None

    def test_seconds(self):
        assert UsageMonitor.parse_retry_after(" 300 ") == 300

    def test_http_date(self):
        assert UsageMonitor.parse_retry_after("Tue, 24 Nov 2026 12:05:00 GMT") == 300

    def test_clamped(self):
        assert UsageMonitor.parse_retry_after("1") == NETWORK_ERROR_RETRY_DELAY
        assert UsageMonitor.parse_retry_after("99999") == RATE_LIMIT_MAX_DELAY
        assert (
            UsageMonitor.parse_retry_after("Tue, 24 Nov 2026 11:00:00 GMT")
            == NETWORK_ERROR_RETRY_DELAY
        )


def test_missing_credentials(display, monkeypatch):
    monkeypatch.setenv("HOME", "/home/pi")
    monitor = make_monitor(display, FileNotFoundError())

    assert monitor.fetch_once() == NO_CREDENTIALS_RETRY_DELAY
    assert monitor.state["error"] == ("No credentials", "~/.usage-monitor/", "credentials.json")
    assert monitor.state["fatal"] is True


class TestNetworkError:
    def test_without_usage(self, display):
        monitor = make_monitor(display, TimeoutError("timed out"))

        assert monitor.fetch_once() == NETWORK_ERROR_RETRY_DELAY
        assert monitor.state == {
            "usage": None,
            "error": ("No network?", "timed out"),
            "fatal": False,
        }

    def test_keeps_known_usage(self, display):
        monitor = make_monitor(display, USAGE, OSError("x" * 50))
        monitor.fetch_once()

        monitor.fetch_once()

        assert monitor.state == {"usage": USAGE, "error": None, "fatal": False}


class TestRenderUsage:
    def test_loading(self, display):
        make_monitor(display).render_usage()

        assert display.last_call == ("loading", 3)

    def test_usage(self, display):
        monitor = make_monitor(display, USAGE)
        monitor.fetch_once()

        monitor.render_usage()

        assert display.last_call == ("usage", USAGE)

    def test_error_without_usage(self, display):
        monitor = make_monitor(display, TimeoutError("timed out"))
        monitor.fetch_once()

        monitor.render_usage()

        assert display.last_call == ("message", ("No network?", "timed out"))

    def test_error_instead_of_stale_usage(self, display):
        monitor = make_monitor(display, USAGE, http_error(USAGE_URL, 500))
        monitor.fetch_once()
        monitor.fetch_once()

        monitor.render_usage()

        assert display.last_call == ("message", ("API error", "HTTP 500", ""))


class TestLoadingScreen:
    def test_animates_until_usage_arrives(self, display, monkeypatch):
        monitor = make_monitor(display, USAGE)
        sleeps = []

        def sleep(seconds):
            sleeps.append(seconds)
            if len(sleeps) == 4:
                monitor.fetch_once()

        monkeypatch.setattr(monitor_module.time, "sleep", sleep)

        monitor.loading_screen()

        assert display.calls == [("loading", 1), ("loading", 2), ("loading", 3), ("loading", 1)]
        assert sleeps == [0.5] * 4

    def test_stops_on_fatal_error(self, display):
        monitor = make_monitor(display)
        monitor.show_fatal_error("API error", "HTTP 500", "")

        monitor.loading_screen()

        assert display.calls == []


def test_fetch_loop_sleeps_returned_delay(display, monkeypatch):
    monitor = make_monitor(display, USAGE, http_error(USAGE_URL, 500))
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise StopLoop

    monkeypatch.setattr(monitor_module.time, "sleep", sleep)

    with pytest.raises(StopLoop):
        monitor.fetch_loop()

    assert sleeps == [monitor.api_request_interval, API_ERROR_RETRY_DELAY]


def test_run(display, monkeypatch):
    monitor = make_monitor(display, USAGE)
    started = []

    class FakeThread:
        def __init__(self, target, daemon):
            started.append((target, daemon))
            target.__self__.fetch_once()  # instead of the endless fetch loop

        def start(self):
            pass

    def sleep(seconds):
        raise StopLoop

    monkeypatch.setattr(monitor_module.threading, "Thread", FakeThread)
    monkeypatch.setattr(monitor_module.time, "sleep", sleep)

    with pytest.raises(StopLoop):
        monitor.run()

    assert started == [(monitor.fetch_loop, True)]
    assert display.calls == [("usage", USAGE)]
