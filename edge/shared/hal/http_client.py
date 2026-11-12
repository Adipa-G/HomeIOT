from edge.shared.hal.interfaces import IHttpClient, IStreamingResponse, HttpResponse

TYPE_CHECKING = False
if TYPE_CHECKING:  # never true on a device; see interfaces.py
    from typing import Any, Protocol

    class _Response(Protocol):
        """What _read_response() uses from a MicroPython (or CPython) requests response."""

        status_code: int

        @property
        def content(self) -> bytes: ...

        def close(self) -> None: ...

_REQUEST_TIMEOUT_S = 30
_POST_OTA_TIMEOUT_S = 10


class StreamingResponse(IStreamingResponse):
    """Wraps a raw socket from MicroPython requests for incremental body reading."""

    def __init__(self, sock: "Any", status_code: int):
        self.status_code = status_code
        # The raw socket MicroPython requests leaves open; None once closed.
        self._sock: "Any" = sock

    def read(self, n: int) -> bytes:
        if self._sock is None:
            raise OSError("Stream is closed")
        return self._sock.read(n)

    def readinto(self, buf: bytearray | memoryview) -> int:
        if self._sock is None:
            raise OSError("Stream is closed")
        return self._sock.readinto(buf)

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None


def _set_socket_timeout(timeout_s: float) -> None:
    try:
        import socket
        socket.setdefaulttimeout(timeout_s)
    except Exception:
        pass  # not available on all builds


def _read_response(response: "_Response") -> HttpResponse:
    """Read status, content, and text from a MicroPython requests response.

    MicroPython's requests closes the socket inside the .content accessor,
    so we read status first, then content (which closes the socket), then
    call .close() as a safety net.
    """
    status_code = response.status_code
    content = response.content if hasattr(response, "content") else b""
    if hasattr(response, "close"):
        response.close()
    text = content.decode("utf-8") if content else ""
    return HttpResponse(status_code=status_code, text=text, content=content)


class MicroPythonHttpClient(IHttpClient):
    def get(self, url: str, headers: dict[str, str] | None = None) -> HttpResponse:
        import requests

        _set_socket_timeout(_REQUEST_TIMEOUT_S)
        response = requests.get(url, headers=headers)
        return _read_response(response)

    def post(
        self,
        url: str,
        data: object,
        headers: dict[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> HttpResponse:
        import requests

        _set_socket_timeout(timeout_s if timeout_s is not None else _REQUEST_TIMEOUT_S)
        response = requests.post(url, json=data, headers=headers)
        return _read_response(response)

    def get_stream(self, url: str, headers: dict[str, str] | None = None) -> StreamingResponse:
        import requests

        _set_socket_timeout(_REQUEST_TIMEOUT_S)
        response = requests.get(url, headers=headers)
        status_code = response.status_code
        if status_code != 200:
            if hasattr(response, "close"):
                response.close()
            raise OSError("OTA stream request failed with HTTP " + str(status_code))
        # Do NOT access .content — leave the raw socket open for incremental reads.
        # MicroPython requests uses HTTP/1.0, so body ends at connection close (no chunked decoding needed).
        return StreamingResponse(response.raw, status_code)
