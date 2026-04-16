import struct

from edge.shared.hal.http_client import _close_response


class FakeRawSocket:
    """Minimal socket stand-in that records setsockopt calls."""

    def __init__(self):
        self.opts = []

    def setsockopt(self, level, optname, value):
        self.opts.append((level, optname, value))


class FakeResponse:
    def __init__(self, raw=None):
        self.raw = raw
        self.closed = False

    def close(self):
        self.closed = True


def test_close_response_sets_so_linger_before_close():
    raw = FakeRawSocket()
    resp = FakeResponse(raw=raw)

    _close_response(resp)

    assert resp.closed
    assert len(raw.opts) == 1
    level, optname, value = raw.opts[0]
    assert level == 1   # SOL_SOCKET
    assert optname == 13  # SO_LINGER
    l_onoff, l_linger = struct.unpack("ii", value)
    assert l_onoff == 1
    assert l_linger == 0


def test_close_response_still_closes_when_setsockopt_fails():
    class BadSocket:
        def setsockopt(self, *args):
            raise OSError("not supported")

    resp = FakeResponse(raw=BadSocket())

    _close_response(resp)

    assert resp.closed


def test_close_response_handles_no_raw():
    resp = FakeResponse(raw=None)

    _close_response(resp)

    assert resp.closed
