from edge.shared.hal.interfaces import IHttpClient, HttpResponse

_REQUEST_TIMEOUT_S = 30


def _set_socket_timeout(timeout_s: int) -> None:
    try:
        import socket
        socket.setdefaulttimeout(timeout_s)
    except Exception:
        pass  # not available on all builds


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
        if hasattr(response, "close"):
            response.close()
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
        if hasattr(response, "close"):
            response.close()
        text = content.decode("utf-8") if content else ""
        return HttpResponse(status_code=status_code, text=text, content=content)
