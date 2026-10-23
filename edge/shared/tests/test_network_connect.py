"""Tests for MicroPythonNetwork.connect() disconnect-before-reconnect logic."""

from edge.shared.hal.network import MicroPythonNetwork
from edge.platforms.esp32.hal.network import MicroPythonNetwork as Esp32Network


class _FakeWlan:
    """Minimal fake wlan matching the MicroPython WLAN interface."""

    PM_NONE = 0
    PM_PERFORMANCE = 1
    PM_POWERSAVE = 2

    def __init__(self, *, connected=False, status=0):
        self._connected = connected
        self._status = status
        self.active_calls = []
        self.connect_calls = []
        self.disconnect_calls = 0
        self.pm_value = None

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

    def config(self, key=None, **kwargs):
        if key == "pm":
            return self.pm_value
        if "pm" in kwargs:
            self.pm_value = kwargs["pm"]


def test_power_save_uses_runtime_wlan_constants():
    wlan = _FakeWlan()
    net = _make_network(wlan)

    assert net.get_power_save_modes() == {
        "none": wlan.PM_NONE,
        "modem": wlan.PM_PERFORMANCE,
        "powersave": wlan.PM_POWERSAVE,
    }
    assert net.set_power_save("powersave") is True
    assert wlan.pm_value == wlan.PM_POWERSAVE


def test_power_save_reports_unsupported_mode():
    class _NoPowerSaveWlan:
        def config(self, **_kwargs):
            raise ValueError("pm unsupported")

    net = _make_network(_NoPowerSaveWlan())

    assert net.get_power_save_modes() == {}
    assert net.set_power_save("modem") is False


def test_esp32_power_save_prefers_named_constants():
    wlan = _FakeWlan()
    net = Esp32Network()
    net._wlan = wlan

    assert net.get_power_save_modes()["modem"] == wlan.PM_PERFORMANCE
    assert net.get_power_save_modes()["powersave"] == wlan.PM_POWERSAVE
    assert net.set_power_save("modem") is True
    assert wlan.pm_value == wlan.PM_PERFORMANCE


def test_esp32_power_save_uses_known_legacy_values_when_constants_are_missing():
    class _LegacyWlan:
        def __init__(self):
            self.pm_value = None

        def config(self, **kwargs):
            self.pm_value = kwargs["pm"]

    wlan = _LegacyWlan()
    net = Esp32Network()
    net._wlan = wlan

    assert net.set_power_save("light") is True
    assert wlan.pm_value == 2


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


def test_connect_always_disconnects_before_reconnect():
    """disconnect() is called unconditionally before wlan.connect() so that
    the ESP-IDF state machine is always in a clean idle state."""
    wlan = _FakeWlan(connected=False, status=0)
    net = _make_network(wlan)

    net.connect("ssid", "pass", timeout_ms=100)

    assert wlan.disconnect_calls == 1
    assert len(wlan.connect_calls) == 1


def test_connect_skips_entirely_when_already_connected():
    """When already connected, connect returns immediately."""
    wlan = _FakeWlan(connected=True, status=0)
    net = _make_network(wlan)

    net.connect("ssid", "pass", timeout_ms=100)

    assert wlan.disconnect_calls == 0
    assert len(wlan.connect_calls) == 0


def test_connect_survives_wlan_without_disconnect_method():
    """If wlan has no disconnect() method (e.g. some Pico ports), connect
    still works — the exception is swallowed."""

    class _NoDisconnectWlan:
        def __init__(self):
            self.connect_calls = []

        def active(self, enable):
            pass

        def isconnected(self):
            return bool(self.connect_calls)

        def connect(self, ssid, password):
            self.connect_calls.append((ssid, password))

    wlan = _NoDisconnectWlan()
    net = _make_network(wlan)

    net.connect("ssid", "pass", timeout_ms=100)

    assert len(wlan.connect_calls) == 1


def test_suspend_disconnects_and_powers_down_radio():
    wlan = _FakeWlan(connected=True)
    net = _make_network(wlan)

    net.suspend()

    assert wlan.disconnect_calls == 1
    assert wlan.active_calls == [False]


def test_suspend_powers_down_even_when_disconnect_fails():
    class _FailingDisconnectWlan(_FakeWlan):
        def disconnect(self):
            raise OSError("not connected")

    wlan = _FailingDisconnectWlan(connected=False)
    net = _make_network(wlan)

    net.suspend()

    assert wlan.active_calls == [False]


def test_connect_after_suspend_reactivates_radio():
    wlan = _FakeWlan(connected=False)
    net = _make_network(wlan)

    net.suspend()
    net.connect("ssid", "pass", timeout_ms=100)

    assert wlan.active_calls == [False, True]
    assert wlan.connect_calls == [("ssid", "pass")]


class _NeverConnectsWlan(_FakeWlan):
    def isconnected(self):
        return False

    def status(self):
        return -2


def _no_wait(net):
    net._sleep_ms = lambda _time_mod, _ms: None


def test_connect_timeout_powers_radio_down_and_reports_status():
    wlan = _NeverConnectsWlan()
    net = _make_network(wlan)
    _no_wait(net)

    try:
        net.connect("ssid", "pass", timeout_ms=0)
        raise AssertionError("expected timeout")
    except RuntimeError as exc:
        assert "status=-2" in str(exc)

    assert wlan.active_calls[-1] is False
    # Pre-connect disconnect plus the one from powering down.
    assert wlan.disconnect_calls == 2


def test_connect_timeout_without_status_method():
    class _NoStatusWlan(_NeverConnectsWlan):
        status = None

    wlan = _NoStatusWlan()
    net = _make_network(wlan)
    _no_wait(net)

    try:
        net.connect("ssid", "pass", timeout_ms=0)
        raise AssertionError("expected timeout")
    except RuntimeError as exc:
        assert "status=None" in str(exc)


def _install_network_module(monkeypatch, country=None, rp2_country=None):
    import sys
    import types

    network_mod = types.ModuleType("network")
    if country is not None:
        network_mod.country = country
    monkeypatch.setitem(sys.modules, "network", network_mod)
    if rp2_country is not None:
        rp2_mod = types.ModuleType("rp2")
        rp2_mod.country = rp2_country
        monkeypatch.setitem(sys.modules, "rp2", rp2_mod)
    else:
        monkeypatch.delitem(sys.modules, "rp2", raising=False)


def test_set_country_uses_network_country(monkeypatch):
    calls = []
    _install_network_module(monkeypatch, country=calls.append)

    assert MicroPythonNetwork().set_country(" au ") is True
    assert calls == ["AU"]


def test_set_country_falls_back_to_rp2_country(monkeypatch):
    calls = []
    _install_network_module(monkeypatch, rp2_country=calls.append)

    assert MicroPythonNetwork().set_country("AU") is True
    assert calls == ["AU"]


def test_set_country_rejects_invalid_code(monkeypatch):
    calls = []
    _install_network_module(monkeypatch, country=calls.append)

    assert MicroPythonNetwork().set_country("AUS") is False
    assert MicroPythonNetwork().set_country("") is False
    assert calls == []


def test_set_country_returns_false_when_setter_fails(monkeypatch):
    def _fail(_code):
        raise ValueError("bad country")

    _install_network_module(monkeypatch, country=_fail)

    assert MicroPythonNetwork().set_country("AU") is False
