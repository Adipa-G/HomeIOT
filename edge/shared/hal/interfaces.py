# Type-only imports: MicroPython has no typing/collections.abc, so this block never runs
# on a device. Annotations that use these names are strings.
TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterable


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

    def listdir(self, path: str) -> list[str]:
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

    def write_chunks(self, path: str, chunks: "Iterable[bytes | bytearray | memoryview]") -> None:
        """Write an iterable of bytes chunks to path without buffering all at once."""
        raise NotImplementedError()


class INetwork:
    def connect(self, ssid: str, password: str, timeout_ms: int = 15000) -> None:
        raise NotImplementedError()

    def is_connected(self) -> bool:
        raise NotImplementedError()

    def get_ip(self) -> str:
        raise NotImplementedError()

    def get_power_save_modes(self) -> dict[str, int]:
        raise NotImplementedError()

    def set_power_save(self, mode: str) -> bool:
        raise NotImplementedError()

    def interface_active(self, enable: bool) -> None:
        raise NotImplementedError()

    def set_country(self, country: str) -> bool:
        """Set the Wi-Fi regulatory country (ISO 3166 alpha-2). Returns False if unsupported."""
        raise NotImplementedError()

    def set_hostname(self, name: str) -> bool:
        """Set the DHCP hostname (sanitized). Call before connect(). Returns False if unsupported."""
        raise NotImplementedError()

    def suspend(self) -> None:
        """Disconnect and power down the radio. connect() brings it back up."""
        raise NotImplementedError()


class HttpResponse:
    def __init__(self, status_code: int, text: str, content: bytes = b""):
        self.status_code = status_code
        self.text = text
        self.content = content


class IStreamingResponse:
    """Body of a streaming GET, read incrementally."""

    status_code: int

    def read(self, n: int) -> bytes:
        raise NotImplementedError()

    def readinto(self, buf: bytearray | memoryview) -> int:
        """Fill buf with up to len(buf) bytes; returns 0 at end of stream."""
        raise NotImplementedError()

    def close(self) -> None:
        raise NotImplementedError()


class IHttpClient:
    def get(self, url: str, headers: dict[str, str] | None = None) -> HttpResponse:
        raise NotImplementedError()

    def post(
        self,
        url: str,
        data: object,
        headers: dict[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> HttpResponse:
        raise NotImplementedError()

    def get_stream(self, url: str, headers: dict[str, str] | None = None) -> IStreamingResponse:
        """Open a streaming GET request."""
        raise NotImplementedError()


class ISystem:
    def reset(self) -> None:
        raise NotImplementedError()

    def unique_id(self) -> str:
        raise NotImplementedError()

    def time_ms(self) -> int:
        raise NotImplementedError()

    def ticks_diff(self, a: int, b: int) -> int:
        """Return a - b, correctly handling wraparound of time_ms() values.

        MicroPython's underlying tick counter wraps periodically, so any
        code that compares or subtracts two time_ms() values must go
        through this method instead of using naive arithmetic.
        """
        raise NotImplementedError()

    def ticks_add(self, ticks: int, delta: int) -> int:
        """Return ticks + delta, safe to use with ticks_diff() later."""
        raise NotImplementedError()

    def uptime_ms(self) -> int:
        raise NotImplementedError()

    def free_memory_bytes(self) -> int:
        raise NotImplementedError()

    def sleep_ms(self, milliseconds: int) -> None:
        raise NotImplementedError()

    def light_sleep_ms(self, milliseconds: int) -> bool:
        """Enter CPU light sleep, preserving RAM. Returns False if it fell back to sleep_ms()."""
        raise NotImplementedError()

    def reset_cause(self) -> str:
        """Return why the device last started, e.g. 'pwron_reset' or 'wdt_reset'."""
        raise NotImplementedError()

    def sync_time(self) -> bool:
        raise NotImplementedError()

    def clock_is_set(self) -> bool:
        """True once the wall clock holds a real date (i.e. it has been synced)."""
        raise NotImplementedError()

    def utc_datetime(self) -> tuple[int, ...]:
        """Current hardware clock as (year, month, day, hour, minute, second) in UTC."""
        raise NotImplementedError()

    def set_utc_datetime(self, parts: tuple[int, ...]) -> None:
        """Set the hardware clock from (year, month, day, hour, minute, second, weekday) in UTC."""
        raise NotImplementedError()


class IWatchdog:
    def init(self, timeout_ms: int) -> None:
        raise NotImplementedError()

    def feed(self) -> None:
        raise NotImplementedError()

    def get_feed_interval_ms(self) -> int | None:
        """Longest safe gap between feeds while sleeping, or None if no limit applies."""
        raise NotImplementedError()
