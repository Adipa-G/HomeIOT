"""Mock HTTP client HAL for PC simulator."""
from io import BytesIO

from edge.shared.hal.interfaces import IHttpClient, HttpResponse

_REQUEST_TIMEOUT_S = 30


class StreamingResponseWrapper:
    """Wraps requests.Response for streaming."""

    def __init__(self, response):
        self._response = response
        self._iter = response.iter_content(chunk_size=4096)

    def read(self, n: int) -> bytes:
        """Read up to n bytes from response."""
        try:
            return next(self._iter)
        except StopIteration:
            return b""

    def close(self) -> None:
        """Close the response."""
        self._response.close()


class SimulatorHttpClient(IHttpClient):
    """HTTP client for PC simulator using standard requests library."""

    def get(self, url: str, headers=None) -> HttpResponse:
        """Perform GET request."""
        import requests
        
        response = requests.get(url, headers=headers, timeout=_REQUEST_TIMEOUT_S)
        return HttpResponse(
            status_code=response.status_code,
            text=response.text,
            content=response.content,
        )

    def post(self, url: str, data, headers=None, timeout_s=None) -> HttpResponse:
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

    def get_stream(self, url: str, headers=None):
        """Open a streaming GET request."""
        import requests
        
        response = requests.get(
            url, headers=headers, timeout=_REQUEST_TIMEOUT_S, stream=True
        )
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
        return StreamingResponseWrapper(response)
