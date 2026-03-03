from edge.shared.hal.interfaces import IFileSystem


def atomic_write_text(fs: IFileSystem, path: str, data: str) -> None:
    atomic_write_bytes(fs, path, data.encode("utf-8"))


def atomic_write_bytes(fs: IFileSystem, path: str, data: bytes) -> None:
    tmp_path = path + ".tmp"
    bak_path = path + ".bak"

    parent = _parent_dir(path)
    if parent and not fs.exists(parent):
        fs.makedirs(parent)

    _remove_if_exists(fs, tmp_path)
    fs.write_bytes(tmp_path, data)

    had_original = fs.exists(path)
    try:
        if had_original:
            _remove_if_exists(fs, bak_path)
            fs.rename(path, bak_path)

        fs.rename(tmp_path, path)
        _remove_if_exists(fs, bak_path)
    except Exception:
        _remove_if_exists(fs, tmp_path)
        if had_original and fs.exists(bak_path) and not fs.exists(path):
            fs.rename(bak_path, path)
        raise


def _remove_if_exists(fs: IFileSystem, path: str) -> None:
    if not fs.exists(path):
        return
    if fs.is_dir(path):
        return
    fs.remove(path)


def _parent_dir(path: str) -> str:
    if "/" not in path:
        return ""
    return path.rsplit("/", 1)[0]