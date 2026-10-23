from edge.shared.hal.network import MicroPythonNetwork


class PicoNetwork(MicroPythonNetwork):
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