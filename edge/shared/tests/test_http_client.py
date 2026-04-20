import io

from edge.shared.hal.http_client import StreamingResponse, _read_response
from edge.shared.hal.interfaces import HttpResponse


class FakeResponse:
    """Mimics urequests.Response: .content closes the socket and sets raw=None."""

    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.closed = False
        self.raw = io.BytesIO(body)

    @property
    def content(self):
        return self._body

    def close(self):
        self.closed = True


def test_read_response_returns_status_and_body():
    resp = FakeResponse(200, b"hello")
    result = _read_response(resp)

    assert result.status_code == 200
    assert result.content == b"hello"
    assert result.text == "hello"
    assert resp.closed


def test_read_response_handles_empty_body():
    resp = FakeResponse(204, b"")
    result = _read_response(resp)

    assert result.status_code == 204
    assert result.content == b""
    assert result.text == ""
    assert resp.closed


def test_streaming_response_read_delegates_to_socket():
    sock = io.BytesIO(b"stream body")
    sr = StreamingResponse(sock, 200)

    assert sr.status_code == 200
    assert sr.read(6) == b"stream"
    assert sr.read(5) == b" body"


def test_streaming_response_close_nulls_socket():
    sock = io.BytesIO(b"data")
    sr = StreamingResponse(sock, 200)
    sr.close()
    assert sr._sock is None


def test_streaming_response_close_is_idempotent():
    sock = io.BytesIO(b"data")
    sr = StreamingResponse(sock, 200)
    sr.close()
    sr.close()  # should not raise


def test_streaming_response_readinto_fills_buffer_and_returns_count():
    sock = io.BytesIO(b"stream body")
    sr = StreamingResponse(sock, 200)
    buf = bytearray(6)
    n = sr.readinto(buf)
    assert n == 6
    assert buf == b"stream"


def test_streaming_response_readinto_partial_at_end():
    sock = io.BytesIO(b"hi")
    sr = StreamingResponse(sock, 200)
    buf = bytearray(10)
    n = sr.readinto(buf)
    assert n == 2
    assert buf[:n] == b"hi"
