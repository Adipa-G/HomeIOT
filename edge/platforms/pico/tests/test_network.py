from edge.platforms.pico.hal.network import PicoNetwork


class _FakeCyw43Wlan:
    def __init__(self, with_deinit=True):
        self.calls = []
        if not with_deinit:
            self.deinit = None

    def disconnect(self):
        self.calls.append("disconnect")

    def active(self, enable):
        self.calls.append(("active", enable))

    def deinit(self):
        self.calls.append("deinit")


def test_suspend_powers_off_cyw43_chip_with_deinit():
    wlan = _FakeCyw43Wlan()
    net = PicoNetwork()
    net._wlan = wlan

    net.suspend()

    assert wlan.calls == ["disconnect", ("active", False), "deinit"]
    # Forces a fresh WLAN handle on the next connect().
    assert net._wlan is None


def test_suspend_without_deinit_keeps_wlan_handle():
    wlan = _FakeCyw43Wlan(with_deinit=False)
    net = PicoNetwork()
    net._wlan = wlan

    net.suspend()

    assert wlan.calls == ["disconnect", ("active", False)]
    assert net._wlan is wlan


def test_connect_timeout_fully_powers_off_cyw43_chip():
    class _NeverConnects(_FakeCyw43Wlan):
        def isconnected(self):
            return False

        def connect(self, ssid, password):
            self.calls.append("connect")

        def status(self):
            return 1

    wlan = _NeverConnects()
    net = PicoNetwork()
    net._wlan = wlan
    net._sleep_ms = lambda _time_mod, _ms: None

    try:
        net.connect("ssid", "pass", timeout_ms=0)
        raise AssertionError("expected timeout")
    except RuntimeError as exc:
        assert "status=1" in str(exc)

    assert wlan.calls[-1] == "deinit"
    assert net._wlan is None
