from edge.platforms.pico.hal.network import PicoNetwork


class _FakeWlanWithoutDeinit:
    def __init__(self):
        self.calls: list[str | tuple[str, bool]] = []

    def disconnect(self) -> None:
        self.calls.append("disconnect")

    def active(self, enable: bool) -> None:
        self.calls.append(("active", enable))


class _FakeCyw43Wlan(_FakeWlanWithoutDeinit):
    def deinit(self) -> None:
        self.calls.append("deinit")


def _make_network(wlan: _FakeWlanWithoutDeinit) -> PicoNetwork:
    net = PicoNetwork()
    # suspend() resets _wlan to None, so pyright narrows the attribute to None.
    setattr(net, "_wlan", wlan)
    return net


def test_suspend_powers_off_cyw43_chip_with_deinit() -> None:
    wlan = _FakeCyw43Wlan()
    net = _make_network(wlan)

    net.suspend()

    assert wlan.calls == ["disconnect", ("active", False), "deinit"]
    # Forces a fresh WLAN handle on the next connect().
    assert net._wlan is None


def test_suspend_without_deinit_keeps_wlan_handle() -> None:
    wlan = _FakeWlanWithoutDeinit()
    net = _make_network(wlan)

    net.suspend()

    assert wlan.calls == ["disconnect", ("active", False)]
    assert net._wlan is wlan


def test_connect_timeout_fully_powers_off_cyw43_chip() -> None:
    class _NeverConnects(_FakeCyw43Wlan):
        def isconnected(self) -> bool:
            return False

        def connect(self, ssid: str, password: str) -> None:
            self.calls.append("connect")

        def status(self) -> int:
            return 1

    def no_sleep(time_mod: object, milliseconds: int) -> None:
        pass

    wlan = _NeverConnects()
    net = _make_network(wlan)
    setattr(net, "_sleep_ms", no_sleep)

    try:
        net.connect("ssid", "pass", timeout_ms=0)
        raise AssertionError("expected timeout")
    except RuntimeError as exc:
        assert "status=1" in str(exc)

    assert wlan.calls[-1] == "deinit"
    assert net._wlan is None


class _JoiningCyw43Wlan(_FakeCyw43Wlan):
    PM_NONE = 0x10
    PM_PERFORMANCE = 0xA11142
    PM_POWERSAVE = 0x11

    def __init__(self, connected: bool = False):
        super().__init__()
        self.connected = connected

    def isconnected(self) -> bool:
        return self.connected

    def config(self, **kwargs: object) -> None:
        self.calls.append(("pm", kwargs["pm"] == self.PM_NONE))

    def connect(self, ssid: str, password: str) -> None:
        self.calls.append("connect")
        self.connected = True


def test_connect_joins_with_power_save_disabled() -> None:
    wlan = _JoiningCyw43Wlan()
    net = _make_network(wlan)

    net.connect("ssid", "pass", timeout_ms=100)

    assert wlan.calls == [("active", True), "disconnect", ("pm", True), "connect"]


def test_connect_leaves_power_save_alone_when_already_connected() -> None:
    wlan = _JoiningCyw43Wlan(connected=True)
    net = _make_network(wlan)

    net.connect("ssid", "pass", timeout_ms=100)

    assert wlan.calls == [("active", True)]
