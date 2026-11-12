# Types shared across the edge app, for the type checker only.
#
# This is a stub with no .py counterpart: modules import it inside their
# `if TYPE_CHECKING:` block, and build_artifact.py never ships .pyi files, so it
# costs nothing on a device (which has no typing module anyway).
from typing import Any, Protocol

class Logger(Protocol):
    """The logging calls app code makes: EdgeLogger, the bootstrap ConsoleLogger or a test fake.

    Positional-only (app code never passes these by keyword), so implementations may
    name the parameters however they like.
    """

    def info(self, message: str, context: dict[str, Any] | None = None, /) -> None: ...
    def warn(self, message: str, context: dict[str, Any] | None = None, /) -> None: ...
    def error(self, message: str, context: dict[str, Any] | None = None, /) -> None: ...

class DevCommandReporter(Protocol):
    """What the dev command runner needs from DeviceControlClient."""

    def report_dev_command_result(self, command_id: str, payload: dict[str, Any], /) -> bool: ...

class ModuleHost(Protocol):
    """What ModuleRuntime needs from DeviceControlClient."""

    def get_cached_module_package(self, module_id: str, version: str, /) -> bytes | None: ...
    def report_module_result(self, payload: dict[str, Any], /) -> bool: ...
    def report_module_status(self, payload: dict[str, Any], /) -> bool: ...

class Hasher(Protocol):
    """A hashlib hash object, e.g. hashlib.sha256() (CPython or MicroPython)."""

    def update(self, data: bytes | bytearray | memoryview, /) -> None: ...
    def digest(self) -> bytes: ...
