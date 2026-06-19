"""Mock filesystem HAL for PC simulator."""
import os
from pathlib import Path
from typing import Iterator

from edge.shared.hal.interfaces import IFileSystem


class SimulatorFileSystem(IFileSystem):
    """CPython-compatible filesystem implementation using standard library."""

    def read_text(self, path: str) -> str:
        return Path(path).read_text()

    def write_text(self, path: str, data: str) -> None:
        Path(path).write_text(data)

    def read_bytes(self, path: str) -> bytes:
        return Path(path).read_bytes()

    def write_bytes(self, path: str, data: bytes) -> None:
        Path(path).write_bytes(data)

    def exists(self, path: str) -> bool:
        return Path(path).exists()

    def is_dir(self, path: str) -> bool:
        return Path(path).is_dir()

    def listdir(self, path: str):
        return os.listdir(path)

    def mkdir(self, path: str) -> None:
        Path(path).mkdir()

    def makedirs(self, path: str) -> None:
        Path(path).mkdir(parents=True, exist_ok=True)

    def remove(self, path: str) -> None:
        Path(path).unlink()

    def rmdir(self, path: str) -> None:
        Path(path).rmdir()

    def rename(self, src: str, dst: str) -> None:
        Path(src).rename(dst)

    def write_chunks(self, path: str, chunks: Iterator[bytes]) -> None:
        """Write an iterable of bytes chunks to path without buffering all at once."""
        with open(path, "wb") as f:
            for chunk in chunks:
                f.write(chunk)
