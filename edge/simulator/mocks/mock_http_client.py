"""Mock HTTP client HAL for PC simulator."""
from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from edge.shared.hal.interfaces import IHttpClient, HttpResponse

if TYPE_CHECKING:
    # Imported lazily at runtime so the worker can report a missing install itself.
    import requests

_REQUEST_TIMEOUT_S = 30


class StreamingResponseWrapper:
    """Wraps requests.Response for streaming."""

    def __init__(self, response: requests.Response):
        self._response = response
        self.status_code = response.status_code
        self._iter: Iterator[bytes] = response.iter_content(chunk_size=4096)
        self._pending = b""

    def read(self, n: int) -> bytes:
        """Read up to n bytes from response."""
        if self._pending:
            data, self._pending = self._pending[:n], self._pending[n:]
            return data
        try:
            return next(self._iter)
        except StopIteration:
            return b""

    def readinto(self, buf: bytearray | memoryview) -> int:
        """Fill buf with up to len(buf) bytes; returns 0 at end of stream."""
        if not self._pending:
            self._pending = self.read(len(buf))
        n = min(len(buf), len(self._pending))
        buf[:n] = self._pending[:n]
        self._pending = self._pending[n:]
        return n

    def close(self) -> None:
        """Close the response."""
        self._response.close()


class SimulatorHttpClient(IHttpClient):
    """HTTP client for PC simulator using standard requests library."""

    def get(self, url: str, headers: dict[str, str] | None = None) -> HttpResponse:
        """Perform GET request."""
        import requests

        response = requests.get(url, headers=headers, timeout=_REQUEST_TIMEOUT_S)
        return HttpResponse(
            status_code=response.status_code,
            text=response.text,
            content=response.content,
        )

    def post(
        self,
        url: str,
        data: object,
        headers: dict[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> HttpResponse:
        """Perform POST request with JSON data."""
        import requests

        timeout = timeout_s if timeout_s is not None else _REQUEST_TIMEOUT_S
        response = requests.post(
            url, json=data, headers=headers, timeout=timeout
        )
        return HttpResponse(
            status_code=response.status_code,
            text=response.text,
            content=response.content,
        )

    def get_stream(self, url: str, headers: dict[str, str] | None = None) -> StreamingResponseWrapper:
        """Open a streaming GET request."""
        import requests

        response = requests.get(
            url, headers=headers, timeout=_REQUEST_TIMEOUT_S, stream=True
        )
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
        return StreamingResponseWrapper(response)
