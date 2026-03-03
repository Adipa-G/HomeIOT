class MockFileSystem:
    def __init__(self):
        self.files = {}
        self.directories = {""}

    def read_text(self, path: str) -> str:
        return self.read_bytes(path).decode("utf-8")

    def write_text(self, path: str, data: str) -> None:
        self.write_bytes(path, data.encode("utf-8"))

    def read_bytes(self, path: str) -> bytes:
        path = self._normalize(path)
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]

    def write_bytes(self, path: str, data: bytes) -> None:
        path = self._normalize(path)
        parent = self._parent(path)
        if parent not in self.directories:
            self.makedirs(parent)
        self.files[path] = data

    def exists(self, path: str) -> bool:
        path = self._normalize(path)
        return path in self.files or path in self.directories

    def is_dir(self, path: str) -> bool:
        return self._normalize(path) in self.directories

    def listdir(self, path: str):
        path = self._normalize(path)
        prefix = path + "/" if path else ""
        out = set()

        for directory in self.directories:
            if directory.startswith(prefix) and directory != path:
                child = directory[len(prefix) :].split("/", 1)[0]
                if child:
                    out.add(child)

        for file_path in self.files:
            if file_path.startswith(prefix):
                child = file_path[len(prefix) :].split("/", 1)[0]
                if child:
                    out.add(child)

        return sorted(out)

    def mkdir(self, path: str) -> None:
        path = self._normalize(path)
        parent = self._parent(path)
        if parent and parent not in self.directories:
            raise FileNotFoundError(parent)
        self.directories.add(path)

    def makedirs(self, path: str) -> None:
        path = self._normalize(path)
        if not path:
            return
        current = ""
        for part in path.split("/"):
            current = part if not current else current + "/" + part
            self.directories.add(current)

    def remove(self, path: str) -> None:
        path = self._normalize(path)
        if path in self.files:
            del self.files[path]
            return
        raise FileNotFoundError(path)

    def rmdir(self, path: str) -> None:
        path = self._normalize(path)
        for directory in self.directories:
            if directory.startswith(path + "/"):
                raise OSError("Directory not empty")
        for file_path in self.files:
            if file_path.startswith(path + "/"):
                raise OSError("Directory not empty")
        if path in self.directories:
            self.directories.remove(path)
            return
        raise FileNotFoundError(path)

    def rename(self, src: str, dst: str) -> None:
        src = self._normalize(src)
        dst = self._normalize(dst)
        if src in self.files:
            self.files[dst] = self.files.pop(src)
            return
        if src in self.directories:
            self.directories.add(dst)
            for directory in list(self.directories):
                if directory.startswith(src + "/"):
                    suffix = directory[len(src) :]
                    self.directories.add(dst + suffix)
                    self.directories.remove(directory)
            for file_path in list(self.files.keys()):
                if file_path.startswith(src + "/"):
                    suffix = file_path[len(src) :]
                    self.files[dst + suffix] = self.files.pop(file_path)
            self.directories.remove(src)
            return
        raise FileNotFoundError(src)

    @staticmethod
    def _normalize(path: str) -> str:
        return path.strip("/")

    @staticmethod
    def _parent(path: str) -> str:
        if "/" not in path:
            return ""
        return path.rsplit("/", 1)[0]
