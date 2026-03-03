class MockWatchdog:
    def __init__(self):
        self.timeout_ms = None
        self.feed_calls = 0

    def init(self, timeout_ms: int) -> None:
        self.timeout_ms = timeout_ms

    def feed(self) -> None:
        self.feed_calls += 1
