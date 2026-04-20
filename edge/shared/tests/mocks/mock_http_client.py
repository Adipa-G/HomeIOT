import io
import json

from edge.shared.hal.interfaces import HttpResponse


class MockStreamingResponse:
    """In-memory streaming response backed by BytesIO for tests."""

    def __init__(self, data: bytes, status_code: int = 200):
        self.status_code = status_code
        self._stream = io.BytesIO(data)

    def read(self, n: int) -> bytes:
        return self._stream.read(n)

    def readinto(self, buf) -> int:
        data = self._stream.read(len(buf))
        n = len(data)
        buf[:n] = data
        return n

    def close(self) -> None:
        self._stream.close()


class MockHttpClient:
    def __init__(self):
        self.calls = []
        self._responses = {}
        self._stream_responses = {}

    def add_json_response(self, method: str, url: str, status_code: int, payload):
        body = json.dumps(payload)
        self._responses[(method.upper(), url)] = HttpResponse(
            status_code=status_code,
            text=body,
            content=body.encode("utf-8"),
        )

    def add_bytes_response(self, method: str, url: str, status_code: int, content: bytes):
        self._responses[(method.upper(), url)] = HttpResponse(
            status_code=status_code,
            text=content.decode("utf-8", errors="ignore"),
            content=content,
        )

    def add_stream_response(self, url: str, data: bytes, status_code: int = 200):
        self._stream_responses[url] = MockStreamingResponse(data, status_code)

    def get(self, url, headers=None):
        self.calls.append(("GET", url, None, headers or {}))
        return self._responses.get(("GET", url), HttpResponse(404, "", b""))

    def post(self, url, data, headers=None):
        self.calls.append(("POST", url, data, headers or {}))
        return self._responses.get(("POST", url), HttpResponse(200, "{}", b"{}"))

    def get_stream(self, url, headers=None):
        self.calls.append(("GET_STREAM", url, None, headers or {}))
        resp = self._stream_responses.get(url)
        if resp is None:
            return MockStreamingResponse(b"", 404)
        return resp