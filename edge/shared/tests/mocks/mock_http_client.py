import json

from edge.shared.hal.interfaces import HttpResponse


class MockHttpClient:
    def __init__(self):
        self.calls = []
        self._responses = {}

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

    def get(self, url, headers=None):
        self.calls.append(("GET", url, None, headers or {}))
        return self._responses.get(("GET", url), HttpResponse(404, "", b""))

    def post(self, url, data, headers=None):
        self.calls.append(("POST", url, data, headers or {}))
        return self._responses.get(("POST", url), HttpResponse(200, "{}", b"{}"))
