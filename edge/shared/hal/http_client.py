from edge.shared.hal.interfaces import IHttpClient, HttpResponse

_REQUEST_TIMEOUT_S = 30


class StreamingResponse:
    """Wraps a raw socket from urequests for incremental body reading."""

    def __init__(self, sock, status_code: int):
        self.status_code = status_code
        self._sock = sock

    def read(self, n: int) -> bytes:
        return self._sock.read(n)

    def readinto(self, buf) -> int:
        return self._sock.readinto(buf)

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None


def _set_socket_timeout(timeout_s: int) -> None:
    try:
        import socket
        socket.setdefaulttimeout(timeout_s)
    except Exception:
        pass  # not available on all builds


def _read_response(response):
    """Read status, content, and text from a urequests response.

    MicroPython's urequests closes the socket inside the .content accessor,
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
    def get(self, url, headers=None):
        try:
            import urequests as requests
        except ImportError:  # pragma: no cover - desktop fallback
            import requests

        _set_socket_timeout(_REQUEST_TIMEOUT_S)
        response = requests.get(url, headers=headers)
        return _read_response(response)

    def post(self, url, data, headers=None):
        try:
            import urequests as requests
        except ImportError:  # pragma: no cover - desktop fallback
            import requests

        _set_socket_timeout(_REQUEST_TIMEOUT_S)
        response = requests.post(url, json=data, headers=headers)
        return _read_response(response)

    def get_stream(self, url, headers=None):
        try:
            import urequests as requests
        except ImportError:  # pragma: no cover - desktop fallback
            import requests

        _set_socket_timeout(_REQUEST_TIMEOUT_S)
        response = requests.get(url, headers=headers)
        status_code = response.status_code
        if status_code != 200:
            if hasattr(response, "close"):
                response.close()
            raise OSError("OTA stream request failed with HTTP " + str(status_code))
        # Do NOT access .content — leave the raw socket open for incremental reads.
        # urequests uses HTTP/1.0, so body ends at connection close (no chunked decoding needed).
        return StreamingResponse(response.raw, status_code)
