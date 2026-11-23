from edge.platforms.pico.hal.network import DHCP_REFRESH_MS, PicoNetwork


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
    LEASE = ("192.168.68.57", "255.255.252.0", "192.168.68.1", "8.8.8.8")

    def __init__(self, connected: bool = False):
        super().__init__()
        self.connected = connected
        self.addresses = self.LEASE

    def isconnected(self) -> bool:
        return self.connected

    def config(self, **kwargs: object) -> None:
        self.calls.append(("pm", kwargs["pm"] == self.PM_NONE))

    def ifconfig(
        self, addresses: tuple[str, str, str, str] | None = None
    ) -> tuple[str, str, str, str]:
        if addresses is not None:
            self.calls.append(("static", addresses == self.LEASE))
            self.addresses = addresses
        return self.addresses

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


class _Clock:
    def __init__(self):
        self.now_ms = 0

    def __call__(self) -> int:
        return self.now_ms


def _wake(net: PicoNetwork, wlan: _JoiningCyw43Wlan) -> None:
    # suspend() powers the chip off and drops the handle; model a fresh one.
    wlan.connected = False
    wlan.calls.clear()
    setattr(net, "_wlan", wlan)


def _leasing_network(wlan: _JoiningCyw43Wlan) -> tuple[PicoNetwork, _Clock]:
    net = _make_network(wlan)
    clock = _Clock()
    setattr(net, "_now_ms", clock)
    return net, clock


def test_reconnect_reuses_dhcp_address_without_dhcp() -> None:
    wlan = _JoiningCyw43Wlan()
    net, clock = _leasing_network(wlan)

    net.connect("ssid", "pass", timeout_ms=100)
    assert ("static", True) not in wlan.calls

    _wake(net, wlan)
    clock.now_ms = DHCP_REFRESH_MS - 1
    net.connect("ssid", "pass", timeout_ms=100)

    assert wlan.calls == [("active", True), "disconnect", ("pm", True), ("static", True), "connect"]


def test_reconnect_uses_dhcp_again_once_lease_is_due_for_refresh() -> None:
    wlan = _JoiningCyw43Wlan()
    net, clock = _leasing_network(wlan)
    net.connect("ssid", "pass", timeout_ms=100)

    _wake(net, wlan)
    clock.now_ms = DHCP_REFRESH_MS
    net.connect("ssid", "pass", timeout_ms=100)
    assert ("static", True) not in wlan.calls

    # The fresh DHCP lease is reused from then on.
    _wake(net, wlan)
    clock.now_ms = DHCP_REFRESH_MS + 1
    net.connect("ssid", "pass", timeout_ms=100)
    assert ("static", True) in wlan.calls


def test_reconnect_ignores_lease_from_another_ssid() -> None:
    wlan = _JoiningCyw43Wlan()
    net, _ = _leasing_network(wlan)
    net.connect("ssid", "pass", timeout_ms=100)

    _wake(net, wlan)
    net.connect("other", "pass", timeout_ms=100)

    assert ("static", True) not in wlan.calls


def test_failed_join_with_reused_address_falls_back_to_dhcp() -> None:
    class _SecondJoinFails(_JoiningCyw43Wlan):
        def __init__(self):
            super().__init__()
            self.joins = 0

        def connect(self, ssid: str, password: str) -> None:
            self.calls.append("connect")
            self.joins += 1
            self.connected = self.joins == 1

    def no_sleep(time_mod: object, milliseconds: int) -> None:
        pass

    wlan = _SecondJoinFails()
    net, _ = _leasing_network(wlan)
    setattr(net, "_sleep_ms", no_sleep)
    net.connect("ssid", "pass", timeout_ms=100)

    _wake(net, wlan)
    try:
        net.connect("ssid", "pass", timeout_ms=0)
        raise AssertionError("expected timeout")
    except RuntimeError:
        pass

    assert ("static", True) in wlan.calls
    assert net._lease is None
