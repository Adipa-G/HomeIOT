import pytest

from edge.shared.app.safe_io import atomic_write_bytes, atomic_write_text
from edge.shared.tests.mocks.mock_filesystem import MockFileSystem


class RenameFailingFS(MockFileSystem):
    def __init__(self, fail_on_nth_rename: int):
        super().__init__()
        self._rename_count = 0
        self._fail_on_nth_rename = fail_on_nth_rename

    def rename(self, src: str, dst: str) -> None:
        self._rename_count += 1
        if self._rename_count == self._fail_on_nth_rename:
            raise OSError("simulated power-loss during rename")
        super().rename(src, dst)


def test_atomic_write_text_replaces_existing_file():
    fs = MockFileSystem()
    fs.write_text("state.json", "old")

    atomic_write_text(fs, "state.json", "new")

    assert fs.read_text("state.json") == "new"
    assert not fs.exists("state.json.bak")
    assert not fs.exists("state.json.tmp")


def test_atomic_write_restores_original_when_second_rename_fails():
    fs = RenameFailingFS(fail_on_nth_rename=2)
    fs.write_bytes("app/file.txt", b"stable")

    with pytest.raises(OSError):
        atomic_write_bytes(fs, "app/file.txt", b"new-content")

    assert fs.read_bytes("app/file.txt") == b"stable"
    assert not fs.exists("app/file.txt.tmp")
