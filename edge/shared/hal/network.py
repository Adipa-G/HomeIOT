from edge.shared.hal.interfaces import INetwork


class MicroPythonNetwork(INetwork):
    _POWER_SAVE_CONSTANTS = {
        "none": "PM_NONE",
        "modem": "PM_PERFORMANCE",
        "powersave": "PM_POWERSAVE",
    }

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

        # Always disconnect before attempting a new connection to reset the
        # ESP-IDF state machine.  Calling wlan.connect() while the driver is
        # in any non-idle state (connecting, retrying, assoc tear-down, etc.)
        # causes "wifi:sta is connecting, cannot set config".
        try:
            wlan.disconnect()
        except Exception:
            pass

        wlan.connect(ssid, password)

        try:
            import utime as _time
        except ImportError:  # pragma: no cover - desktop fallback
            import time as _time

        started = self._ticks_ms(_time)
        while not wlan.isconnected():
            if self._ticks_diff(self._ticks_ms(_time), started) > timeout_ms:
                status = self._read_status(wlan)
                # Left alone, the driver keeps scanning/joining at full radio
                # power in the background; power it down until the next attempt.
                try:
                    self.suspend()
                except Exception:
                    pass
                raise RuntimeError("WiFi connection timed out (status=" + str(status) + ")")
            self._sleep_ms(_time, 200)

    def set_country(self, country: str) -> bool:
        code = str(country or "").strip().upper()
        if len(code) != 2:
            return False
        try:
            import network
        except ImportError:  # pragma: no cover - desktop fallback
            return False
        # Must run before the radio powers up; the country is kept across deinit().
        setter = getattr(network, "country", None)
        if not callable(setter):
            try:
                import rp2
                setter = getattr(rp2, "country", None)
            except ImportError:
                setter = None
        if not callable(setter):
            return False
        try:
            setter(code)
            return True
        except Exception:
            return False

    @staticmethod
    def _read_status(wlan):
        status = getattr(wlan, "status", None)
        if not callable(status):
            return None
        try:
            return status()
        except Exception:
            return None

    def is_connected(self) -> bool:
        return self._get_wlan().isconnected()

    def get_ip(self) -> str:
        return self._get_wlan().ifconfig()[0]

    def get_power_save_modes(self) -> dict:
        wlan = self._get_wlan()
        if not callable(getattr(wlan, "config", None)):
            return {}

        modes = {}
        for mode, constant_name in self._POWER_SAVE_CONSTANTS.items():
            if hasattr(wlan, constant_name):
                modes[mode] = getattr(wlan, constant_name)
        return modes

    def set_power_save(self, mode: str) -> bool:
        wlan = self._get_wlan()
        normalized = str(mode or "none").lower()
        if normalized == "light":
            normalized = "powersave"
        pm_modes = self.get_power_save_modes()
        if normalized not in pm_modes:
            return False

        try:
            self._set_power_save_value(wlan, pm_modes[normalized])
            return True
        except Exception:
            return False

    @staticmethod
    def _set_power_save_value(wlan, pm_value):
        wlan.config(pm=pm_value)

    def interface_active(self, enable: bool) -> None:
        self._get_wlan().active(bool(enable))

    def suspend(self) -> None:
        wlan = self._get_wlan()
        try:
            wlan.disconnect()
        except Exception:
            pass
        # On the Pico W this also shuts the CYW43 chip down; lightsleep()
        # returns immediately while it has pending work.
        wlan.active(False)

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
