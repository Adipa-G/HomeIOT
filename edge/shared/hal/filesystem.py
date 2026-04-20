try:
    import uos as _os
except ImportError:  # pragma: no cover - desktop fallback
    import os as _os

from edge.shared.hal.interfaces import IFileSystem


class MicroPythonFileSystem(IFileSystem):
    def read_text(self, path: str) -> str:
        with open(path, "r") as handle:
            return handle.read()

    def write_text(self, path: str, data: str) -> None:
        with open(path, "w") as handle:
            handle.write(data)

    def read_bytes(self, path: str) -> bytes:
        with open(path, "rb") as handle:
            return handle.read()

    def write_bytes(self, path: str, data: bytes) -> None:
        with open(path, "wb") as handle:
            handle.write(data)

    def exists(self, path: str) -> bool:
        try:
            _os.stat(path)
            return True
        except OSError:
            return False

    def is_dir(self, path: str) -> bool:
        try:
            mode = _os.stat(path)[0]
            return (mode & 0x4000) == 0x4000
        except OSError:
            return False

    def listdir(self, path: str):
        return _os.listdir(path)

    def mkdir(self, path: str) -> None:
        _os.mkdir(path)

    def makedirs(self, path: str) -> None:
        if not path:
            return
        parts = [part for part in path.split("/") if part]
        current = ""
        for part in parts:
            current = current + "/" + part if current else part
            if not self.exists(current):
                _os.mkdir(current)

    def remove(self, path: str) -> None:
        _os.remove(path)

    def rmdir(self, path: str) -> None:
        _os.rmdir(path)

    def rename(self, src: str, dst: str) -> None:
        _os.rename(src, dst)

    def write_chunks(self, path: str, chunks) -> None:
        with open(path, "wb") as handle:
            for chunk in chunks:
                handle.write(chunk)
