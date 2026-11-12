from edge.shared.hal.interfaces import INetwork


class MockNetwork(INetwork):
    def __init__(self, ip: str = "192.168.1.20"):
        self.connected = False
        self.ip = ip
        self.connect_calls: list[tuple[str, str, int]] = []
        self.suspend_calls = 0
        self.country: str | None = None
        self.hostname: str | None = None

    def set_country(self, country: str) -> bool:
        self.country = country
        return True

    def set_hostname(self, name: str) -> bool:
        self.hostname = name
        return True

    def connect(self, ssid: str, password: str, timeout_ms: int = 15000) -> None:
        self.connect_calls.append((ssid, password, timeout_ms))
        self.connected = True

    def suspend(self) -> None:
        self.suspend_calls += 1
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    def get_ip(self) -> str:
        return self.ip
