from edge.shared.hal.interfaces import IHttpClient, HttpResponse

_REQUEST_TIMEOUT_S = 30


def _set_socket_timeout(timeout_s: int) -> None:
    try:
        import socket
        socket.setdefaulttimeout(timeout_s)
    except Exception:
        pass  # not available on all builds


def _close_response(response) -> None:
    """Close response socket with SO_LINGER(0) to send RST and skip TIME_WAIT.

    Without this, each closed socket sits in TIME_WAIT for ~120 s on ESP32's
    lwIP stack.  The TIME_WAIT PCB pool is tiny (~5 slots), so rapid sequential
    requests (e.g. OTA file downloads) exhaust it and new connect() calls stall.
    Forcing RST frees the PCB immediately.
    """
    raw = getattr(response, "raw", None)
    if raw is not None:
        try:
            import struct
            # SOL_SOCKET = 1, SO_LINGER = 13 on lwIP / ESP32
            raw.setsockopt(1, 13, struct.pack("ii", 1, 0))
        except Exception:
            pass
    if hasattr(response, "close"):
        response.close()


class MicroPythonHttpClient(IHttpClient):
    def get(self, url, headers=None):
        try:
            import urequests as requests
        except ImportError:  # pragma: no cover - desktop fallback
            import requests

        _set_socket_timeout(_REQUEST_TIMEOUT_S)
        response = requests.get(url, headers=headers)
        status_code = response.status_code
        # Read content (bytes) first; derive text from it to avoid
        # holding two copies of the body in memory simultaneously.
        content = response.content if hasattr(response, "content") else b""
        _close_response(response)
        text = content.decode("utf-8") if content else ""
        return HttpResponse(status_code=status_code, text=text, content=content)

    def post(self, url, data, headers=None):
        try:
            import urequests as requests
        except ImportError:  # pragma: no cover - desktop fallback
            import requests

        _set_socket_timeout(_REQUEST_TIMEOUT_S)
        response = requests.post(url, json=data, headers=headers)
        status_code = response.status_code
        content = response.content if hasattr(response, "content") else b""
        _close_response(response)
        text = content.decode("utf-8") if content else ""
        return HttpResponse(status_code=status_code, text=text, content=content)
