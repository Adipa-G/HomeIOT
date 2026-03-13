from edge.shared.hal.interfaces import INetwork


class MicroPythonNetwork(INetwork):
    def __init__(self):
        self._wlan = None

    def _get_wlan(self):
        if self._wlan is None:
            try:
                import network
            except ImportError as exc:  # pragma: no cover - desktop fallback
                raise RuntimeError("network module is not available") from exc
            self._wlan = network.WLAN(network.STA_IF)
        return self._wlan

    def connect(self, ssid: str, password: str, timeout_ms: int = 15000) -> None:
        wlan = self._get_wlan()
        wlan.active(True)
        if wlan.isconnected():
            return

        wlan.connect(ssid, password)

        try:
            import utime as _time
        except ImportError:  # pragma: no cover - desktop fallback
            import time as _time

        started = self._ticks_ms(_time)
        while not wlan.isconnected():
            if self._ticks_diff(self._ticks_ms(_time), started) > timeout_ms:
                raise RuntimeError("WiFi connection timed out")
            self._sleep_ms(_time, 200)

    def is_connected(self) -> bool:
        return self._get_wlan().isconnected()

    def get_ip(self) -> str:
        return self._get_wlan().ifconfig()[0]

    def set_power_save(self, mode: str) -> None:
        wlan = self._get_wlan()
        normalized = str(mode or "none").lower()
        pm_value = {
            "none": 0,
            "modem": 1,
            "light": 2,
        }.get(normalized, 0)

        if hasattr(wlan, "config"):
            try:
                wlan.config(pm=pm_value)
            except Exception:
                # Not all MicroPython ports expose pm config.
                pass

    def interface_active(self, enable: bool) -> None:
        self._get_wlan().active(bool(enable))

    @staticmethod
    def _ticks_ms(time_mod):
        if hasattr(time_mod, "ticks_ms"):
            return time_mod.ticks_ms()
        return int(time_mod.time() * 1000)

    @staticmethod
    def _ticks_diff(newer, older):
        return newer - older

    @staticmethod
    def _sleep_ms(time_mod, milliseconds):
        if hasattr(time_mod, "sleep_ms"):
            time_mod.sleep_ms(milliseconds)
        else:
            time_mod.sleep(milliseconds / 1000)
