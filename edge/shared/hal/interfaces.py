class IFileSystem:
    def read_text(self, path: str) -> str:
        raise NotImplementedError()

    def write_text(self, path: str, data: str) -> None:
        raise NotImplementedError()

    def read_bytes(self, path: str) -> bytes:
        raise NotImplementedError()

    def write_bytes(self, path: str, data: bytes) -> None:
        raise NotImplementedError()

    def exists(self, path: str) -> bool:
        raise NotImplementedError()

    def is_dir(self, path: str) -> bool:
        raise NotImplementedError()

    def listdir(self, path: str):
        raise NotImplementedError()

    def mkdir(self, path: str) -> None:
        raise NotImplementedError()

    def makedirs(self, path: str) -> None:
        raise NotImplementedError()

    def remove(self, path: str) -> None:
        raise NotImplementedError()

    def rmdir(self, path: str) -> None:
        raise NotImplementedError()

    def rename(self, src: str, dst: str) -> None:
        raise NotImplementedError()

    def write_chunks(self, path: str, chunks) -> None:
        """Write an iterable of bytes chunks to path without buffering all at once."""
        raise NotImplementedError()


class INetwork:
    def connect(self, ssid: str, password: str, timeout_ms: int = 15000) -> None:
        raise NotImplementedError()

    def is_connected(self) -> bool:
        raise NotImplementedError()

    def get_ip(self) -> str:
        raise NotImplementedError()

    def set_power_save(self, mode: str) -> None:
        raise NotImplementedError()

    def interface_active(self, enable: bool) -> None:
        raise NotImplementedError()


class HttpResponse:
    def __init__(self, status_code: int, text: str, content: bytes = b""):
        self.status_code = status_code
        self.text = text
        self.content = content


class IHttpClient:
    def get(self, url: str, headers=None) -> HttpResponse:
        raise NotImplementedError()

    def post(
        self,
        url: str,
        data,
        headers=None,
        timeout_s=None,
    ) -> HttpResponse:
        raise NotImplementedError()

    def get_stream(self, url: str, headers=None):
        """Open a streaming GET request. Returns an object with read(n) and close() methods."""
        raise NotImplementedError()


class ISystem:
    def reset(self) -> None:
        raise NotImplementedError()

    def unique_id(self) -> str:
        raise NotImplementedError()

    def time_ms(self) -> int:
        raise NotImplementedError()

    def uptime_ms(self) -> int:
        raise NotImplementedError()

    def free_memory_bytes(self) -> int:
        raise NotImplementedError()

    def sleep_ms(self, milliseconds: int) -> None:
        raise NotImplementedError()

    def sync_time(self) -> bool:
        raise NotImplementedError()


class IWatchdog:
    def init(self, timeout_ms: int) -> None:
        raise NotImplementedError()

    def feed(self) -> None:
        raise NotImplementedError()
