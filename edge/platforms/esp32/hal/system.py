from edge.shared.hal.system import MicroPythonSystem as _SharedMicroPythonSystem

# machine.lightsleep() hangs on ESP32-C6 in MicroPython 1.27-1.29 until the LP
# watchdog resets the chip (micropython/micropython#19396). Fixed in 1.30 by the
# move to ESP-IDF v5.5.5 (micropython/micropython#19558).
_BROKEN_LIGHTSLEEP_CHIPS = ("ESP32C6",)
_BROKEN_LIGHTSLEEP_SINCE = (1, 27)
_BROKEN_LIGHTSLEEP_UNTIL = (1, 29)


def _parse_version(value):
    parts = []
    for part in str(value or "").split("."):
        digits = ""
        for char in part:
            if not char.isdigit():
                break
            digits += char
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def lightsleep_known_broken(capabilities) -> bool:
    machine = str(capabilities.get("machine", "")).upper().replace("-", "")
    if not any(chip in machine for chip in _BROKEN_LIGHTSLEEP_CHIPS):
        return False
    version = _parse_version(capabilities.get("runtime_version"))
    minor = version[:2]
    return bool(version) and _BROKEN_LIGHTSLEEP_SINCE <= minor <= _BROKEN_LIGHTSLEEP_UNTIL


class MicroPythonSystem(_SharedMicroPythonSystem):
    def __init__(self):
        super().__init__()
        self._lightsleep_broken = None

    def get_sleep_capabilities(self) -> dict:
        capabilities = super().get_sleep_capabilities()
        if capabilities.get("lightsleep") and lightsleep_known_broken(capabilities):
            capabilities["lightsleep"] = False
            capabilities["lightsleep_disabled"] = "micropython#19396"
        return capabilities

    def light_sleep_ms(self, milliseconds: int) -> bool:
        if self._lightsleep_broken is None:
            self._lightsleep_broken = lightsleep_known_broken(super().get_sleep_capabilities())
        if self._lightsleep_broken:
            self.sleep_ms(milliseconds)
            return False
        return super().light_sleep_ms(milliseconds)


__all__ = ["MicroPythonSystem"]