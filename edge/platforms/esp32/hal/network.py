from edge.shared.hal.network import MicroPythonNetwork as _SharedMicroPythonNetwork


class MicroPythonNetwork(_SharedMicroPythonNetwork):
	_PM_BY_MODE = {
		"none": 0,
		"modem": 1,
		"light": 2,
	}

	def set_power_save(self, mode: str) -> None:
		wlan = self._get_wlan()
		normalized = str(mode or "none").lower()
		pm_value = self._PM_BY_MODE.get(normalized, self._PM_BY_MODE["none"])

		if hasattr(wlan, "config"):
			try:
				wlan.config(pm=pm_value)
				return
			except Exception:
				pass

		# Fallback for ports exposing powersave as a method.
		if hasattr(wlan, "powersave"):
			try:
				wlan.powersave(pm_value)
			except Exception:
				pass


__all__ = ["MicroPythonNetwork"]
