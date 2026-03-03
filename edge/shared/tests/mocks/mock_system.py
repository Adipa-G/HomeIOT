class MockSystem:
    def __init__(self):
        self.reset_calls = 0
        self.sleep_calls = []
        self._time_ms = 1000

    def reset(self) -> None:
        self.reset_calls += 1

    def unique_id(self) -> str:
        return "mock-device-id"

    def time_ms(self) -> int:
        self._time_ms += 100
        return self._time_ms

    def sleep_ms(self, milliseconds: int) -> None:
        self.sleep_calls.append(milliseconds)
