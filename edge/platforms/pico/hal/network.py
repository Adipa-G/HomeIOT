from edge.shared.hal.network import MicroPythonNetwork


class PicoNetwork(MicroPythonNetwork):
    def _prepare_join(self) -> None:
        # active(True) resets the CYW43 (Pico W / Pico 2 W) to its default
        # power-save mode (PM_PERFORMANCE, 0xa11142), which can make joins
        # flaky. Join with power-save off (PM_NONE, same mode as 0xa11140);
        # the control loop re-applies the configured mode once connected.
        self.set_power_save("none")

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