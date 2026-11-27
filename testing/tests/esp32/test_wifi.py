import pytest

from display_usage.errors import WifiError


@pytest.fixture
def network(micropython_modules):
    return micropython_modules[1]


@pytest.fixture
def clock(micropython_modules):
    return micropython_modules[0]


@pytest.fixture
def wifi_module(micropython_modules):
    from display_usage.esp32 import wifi

    return wifi


@pytest.fixture
def wifi(wifi_module):
    return wifi_module.Wifi("Home", "secret")


def test_init(wifi, network):
    assert (wifi.ssid, wifi.password) == ("Home", "secret")
    assert network.hostnames == ["usage-monitor"]
    assert wifi.wlan.interface == network.STA_IF
    assert wifi.wlan.is_active is True
    assert wifi.wlan.settings == {}


def test_init_with_options(wifi_module, network):
    wifi = wifi_module.Wifi("Home", "secret", hostname="claude", tx_power=8.5)

    assert network.hostnames == ["claude"]
    assert wifi.wlan.settings == {"txpower": 8.5}


def test_starts_connecting(wifi):
    assert wifi.connect() is False
    assert wifi.wlan.connect_calls == [("Home", "secret")]


def test_waits_while_connecting(wifi, network):
    wifi.wlan.state = network.STAT_CONNECTING

    assert wifi.connect() is False
    assert wifi.wlan.connect_calls == []


def test_driver_busy(wifi, capsys):
    wifi.wlan.connect_error = OSError("Wifi Internal Error")

    assert wifi.connect() is False
    assert "Wi-Fi: Wifi Internal Error" in capsys.readouterr().err


@pytest.mark.parametrize(
    "status, message",
    [("STAT_WRONG_PASSWORD", "Wrong password"), ("STAT_NO_AP_FOUND", "Not found")],
)
def test_known_errors(wifi, network, status, message):
    wifi.wlan.state = getattr(network, status)

    with pytest.raises(WifiError) as error:
        wifi.connect()

    assert str(error.value) == message
    assert wifi.wlan.connect_calls == [("Home", "secret")]  # tries again anyway


def test_connected_syncs_clock(wifi, clock):
    wifi.wlan.connected = True

    assert wifi.connect() is True
    assert clock.synced == 1
    assert wifi.wlan.connect_calls == []


def test_clock_sync_interval(wifi, wifi_module, clock):
    wifi.wlan.connected = True
    clock.ms = 5000
    wifi.connect()

    clock.ms += wifi_module.CLOCK_SYNC_INTERVAL - 1
    wifi.connect()
    assert clock.synced == 1

    clock.ms += 1
    wifi.connect()
    assert clock.synced == 2
