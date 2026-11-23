from edge.shared.hal.network import MicroPythonNetwork

TYPE_CHECKING = False
if TYPE_CHECKING:  # never true on a device; see edge/shared/hal/interfaces.py
    from types import ModuleType

# A reused address skips DHCP, so the router's lease isn't renewed. Run DHCP
# again at least this often so the lease never lapses while it's in use.
DHCP_REFRESH_MS = 3600000


class PicoNetwork(MicroPythonNetwork):
    def __init__(self):
        super().__init__()
        # (ssid, ifconfig tuple, ticks when DHCP assigned it), kept in RAM only.
        self._lease: tuple[str, tuple[str, str, str, str], int] | None = None
        self._join_ssid = ""
        self._joined = False
        self._reused_lease = False

    def connect(self, ssid: str, password: str, timeout_ms: int = 15000) -> None:
        self._join_ssid = ssid
        self._joined = False
        self._reused_lease = False
        try:
            super().connect(ssid, password, timeout_ms)
        except Exception:
            if self._reused_lease:
                # The saved address may no longer suit the network; use DHCP next time.
                self._lease = None
            raise
        if self._joined and not self._reused_lease:
            self._remember_lease(ssid)

    def _prepare_join(self) -> None:
        self._joined = True
        # active(True) resets the CYW43 (Pico W / Pico 2 W) to its default
        # power-save mode (PM_PERFORMANCE, 0xa11142), which can make joins
        # flaky. Join with power-save off (PM_NONE, same mode as 0xa11140);
        # the control loop re-applies the configured mode once connected.
        self.set_power_save("none")
        self._reuse_lease()

    def _reuse_lease(self) -> None:
        # deinit() and active(False) clear the address and active(True)
        # restarts DHCP, so each wake would otherwise wait for a fresh lease.
        # Setting the address stops DHCP, and it holds through connect().
        lease = self._lease
        if lease is None or lease[0] != self._join_ssid:
            return
        age_ms = self._age_ms(lease[2])
        if age_ms < 0 or age_ms >= DHCP_REFRESH_MS:
            self._lease = None
            return
        try:
            self._get_wlan().ifconfig(lease[1])
            self._reused_lease = True
        except Exception:
            self._lease = None

    def _remember_lease(self, ssid: str) -> None:
        try:
            ip, mask, gateway, dns = self._get_wlan().ifconfig()
        except Exception:
            return
        if ip and ip != "0.0.0.0":
            self._lease = (ssid, (ip, mask, gateway, dns), self._now_ms())

    def _now_ms(self) -> int:
        import time

        return self._ticks_ms(time)

    def _age_ms(self, since_ms: int) -> int:
        import time

        return self._ticks_since(time, self._now_ms(), since_ms)

    @staticmethod
    def _ticks_since(time_mod: "ModuleType", now_ms: int, since_ms: int) -> int:
        # ticks_diff handles the MicroPython tick counter wrapping around.
        if hasattr(time_mod, "ticks_diff"):
            return time_mod.ticks_diff(now_ms, since_ms)
        return now_ms - since_ms

    def suspend(self) -> None:
        super().suspend()
        # active(False) leaves the CYW43 chip powered (WL_REG_ON high), so it
        # keeps drawing current. deinit() cuts its power; the next
        # connect() -> active(True) powers it up and reloads its firmware.
        deinit = getattr(self._get_wlan(), "deinit", None)
        if callable(deinit):
            deinit()
            self._wlan = None


__all__ = ["PicoNetwork"]