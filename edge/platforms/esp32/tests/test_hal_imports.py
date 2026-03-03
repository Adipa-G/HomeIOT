from edge.platforms.esp32.hal.filesystem import MicroPythonFileSystem
from edge.platforms.esp32.hal.http_client import MicroPythonHttpClient
from edge.platforms.esp32.hal.network import MicroPythonNetwork
from edge.platforms.esp32.hal.system import MicroPythonSystem
from edge.platforms.esp32.hal.watchdog import MicroPythonWatchdog


def test_esp32_hal_classes_import_and_construct():
    assert MicroPythonFileSystem() is not None
    assert MicroPythonHttpClient() is not None
    assert MicroPythonNetwork() is not None
    assert MicroPythonSystem() is not None
    assert MicroPythonWatchdog() is not None
