from edge.platforms.pico.hal.filesystem import PicoFileSystem
from edge.platforms.pico.hal.http_client import PicoHttpClient
from edge.platforms.pico.hal.network import PicoNetwork
from edge.platforms.pico.hal.system import PicoSystem
from edge.platforms.pico.hal.watchdog import PicoWatchdog


def test_pico_hal_classes_import_and_construct():
    assert PicoFileSystem() is not None
    assert PicoHttpClient() is not None
    assert PicoNetwork() is not None
    assert PicoSystem() is not None
    assert PicoWatchdog() is not None
