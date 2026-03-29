"""Tests for MicroPythonNetwork.connect() disconnect-before-reconnect logic."""

from edge.shared.hal.network import MicroPythonNetwork


class _FakeWlan:
    """Minimal fake wlan matching the MicroPython WLAN interface."""

    def __init__(self, *, connected=False, status=0):
        self._connected = connected
        self._status = status
        self.active_calls = []
        self.connect_calls = []
        self.disconnect_calls = 0

    def active(self, enable):
        self.active_calls.append(enable)

    def isconnected(self):
        # After a successful connect call, consider connected.
        if self.connect_calls and self._status != 1:
            return True
        return self._connected

    def status(self):
        return self._status

    def connect(self, ssid, password):
        self.connect_calls.append((ssid, password))
        # Once connect is called, clear the connecting status.
        self._status = 0

    def disconnect(self):
        self.disconnect_calls += 1
        self._status = 0

    def ifconfig(self):
        return ("192.168.1.10", "255.255.255.0", "192.168.1.1", "8.8.8.8")


def _make_network(wlan):
    net = MicroPythonNetwork()
    net._wlan = wlan
    return net


def test_connect_disconnects_when_status_is_connecting():
    """When wlan.status() == STAT_CONNECTING, disconnect is called first."""
    wlan = _FakeWlan(connected=False, status=1)  # 1 == STAT_CONNECTING
    net = _make_network(wlan)

    net.connect("ssid", "pass", timeout_ms=100)

    assert wlan.disconnect_calls == 1
    assert len(wlan.connect_calls) == 1


def test_connect_skips_disconnect_when_not_connecting():
    """When wlan.status() != STAT_CONNECTING, no disconnect is issued."""
    wlan = _FakeWlan(connected=False, status=0)
    net = _make_network(wlan)

    net.connect("ssid", "pass", timeout_ms=100)

    assert wlan.disconnect_calls == 0
    assert len(wlan.connect_calls) == 1


def test_connect_skips_entirely_when_already_connected():
    """When already connected, connect returns immediately."""
    wlan = _FakeWlan(connected=True, status=0)
    net = _make_network(wlan)

    net.connect("ssid", "pass", timeout_ms=100)

    assert wlan.disconnect_calls == 0
    assert len(wlan.connect_calls) == 0


def test_connect_survives_wlan_without_status_method():
    """If wlan has no status() method (e.g. Pico), connect still works."""

    class _NoStatusWlan:
        def __init__(self):
            self.connect_calls = []
            self.disconnect_calls = 0

        def active(self, enable):
            pass

        def isconnected(self):
            return bool(self.connect_calls)

        def connect(self, ssid, password):
            self.connect_calls.append((ssid, password))

    wlan = _NoStatusWlan()
    net = _make_network(wlan)

    net.connect("ssid", "pass", timeout_ms=100)

    assert wlan.disconnect_calls == 0
    assert len(wlan.connect_calls) == 1
