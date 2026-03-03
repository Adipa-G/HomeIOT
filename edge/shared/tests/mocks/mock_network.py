class MockNetwork:
    def __init__(self, ip="192.168.1.20"):
        self.connected = False
        self.ip = ip
        self.connect_calls = []

    def connect(self, ssid: str, password: str, timeout_ms: int = 15000) -> None:
        self.connect_calls.append((ssid, password, timeout_ms))
        self.connected = True

    def is_connected(self) -> bool:
        return self.connected

    def get_ip(self) -> str:
        return self.ip
