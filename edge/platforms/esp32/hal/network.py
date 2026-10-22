from edge.shared.hal.network import MicroPythonNetwork as _SharedMicroPythonNetwork


class MicroPythonNetwork(_SharedMicroPythonNetwork):
	_LEGACY_PM_BY_MODE = {
		"none": 0,
		"modem": 1,
		"powersave": 2,
	}

	def get_power_save_modes(self) -> dict:
		wlan = self._get_wlan()
		modes = super().get_power_save_modes()
		if callable(getattr(wlan, "config", None)) or callable(getattr(wlan, "powersave", None)):
			for mode, value in self._LEGACY_PM_BY_MODE.items():
				modes.setdefault(mode, value)
		return modes

	@staticmethod
	def _set_power_save_value(wlan, pm_value):
		config = getattr(wlan, "config", None)
		if callable(config):
			try:
				config(pm=pm_value)
				return
			except Exception:
				pass

		# Fallback for ports exposing powersave as a method.
		powersave = getattr(wlan, "powersave", None)
		if not callable(powersave):
			raise RuntimeError("Wi-Fi power-save configuration is unsupported")
		powersave(pm_value)


__all__ = ["MicroPythonNetwork"]
