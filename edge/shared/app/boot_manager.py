import json
from typing import Dict

from edge.shared.hal.interfaces import IFileSystem, ISystem
from edge.shared.app.safe_io import atomic_write_bytes, atomic_write_text


class BootManager:
    def __init__(
        self,
        fs: IFileSystem,
        system: ISystem,
        max_attempts: int,
        state_path: str = "boot_state.json",
        app_path: str = "app",
        app_prev_path: str = "app_prev",
        app_staging_path: str = "app_staging",
    ):
        self._fs = fs
        self._system = system
        self._max_attempts = max_attempts
        self._state_path = state_path
        self._app_path = app_path
        self._app_prev_path = app_prev_path
        self._app_staging_path = app_staging_path

    def on_boot(self) -> Dict:
        state = self._load_state()
        state["boot_count"] += 1
        state["boot_succeeded"] = False
        self._save_state(state)

        if state["boot_count"] > self._max_attempts:
            self.rollback()

        return state

    def get_state(self) -> Dict:
        return self._load_state()

    def mark_success(self) -> None:
        state = self._load_state()
        state["boot_count"] = 0
        state["boot_succeeded"] = True
        self._save_state(state)

    def set_new_version(self, version: str) -> None:
        state = self._load_state()

        self._remove_tree(self._app_prev_path)
        if self._fs.exists(self._app_path):
            self._copy_tree(self._app_path, self._app_prev_path)

        self._remove_tree(self._app_path)
        if self._fs.exists(self._app_staging_path):
            self._copy_tree(self._app_staging_path, self._app_path)

        state["previous_version"] = state.get("current_version")
        state["current_version"] = version
        state["boot_count"] = 0
        state["boot_succeeded"] = False
        self._save_state(state)

        self._remove_tree(self._app_staging_path)

    def rollback(self) -> None:
        state = self._load_state()
        if not self._fs.exists(self._app_prev_path):
            raise RuntimeError("Rollback requested but app_prev is missing")

        self._remove_tree(self._app_path)
        self._copy_tree(self._app_prev_path, self._app_path)

        state["current_version"] = state.get("previous_version") or state.get("current_version")
        state["boot_count"] = 0
        state["boot_succeeded"] = False
        self._save_state(state)
        self._system.reset()

    def _load_state(self) -> Dict:
        if not self._fs.exists(self._state_path):
            default_state = {
                "boot_count": 0,
                "boot_succeeded": False,
                "current_version": "0.0.0",
                "previous_version": None,
            }
            self._save_state(default_state)
            return default_state

        return json.loads(self._fs.read_text(self._state_path))

    def _save_state(self, state: Dict) -> None:
        atomic_write_text(self._fs, self._state_path, json.dumps(state))

    def _copy_tree(self, src: str, dst: str) -> None:
        if self._fs.is_dir(src):
            if not self._fs.exists(dst):
                self._fs.makedirs(dst)
            for name in self._fs.listdir(src):
                self._copy_tree(self._join(src, name), self._join(dst, name))
            return

        parent = self._parent_dir(dst)
        if parent and not self._fs.exists(parent):
            self._fs.makedirs(parent)
        atomic_write_bytes(self._fs, dst, self._fs.read_bytes(src))

    def _remove_tree(self, path: str) -> None:
        if not self._fs.exists(path):
            return

        if self._fs.is_dir(path):
            for name in self._fs.listdir(path):
                self._remove_tree(self._join(path, name))
            self._fs.rmdir(path)
            return

        self._fs.remove(path)

    @staticmethod
    def _join(left: str, right: str) -> str:
        if not left:
            return right
        if left.endswith("/"):
            return left + right
        return left + "/" + right

    @staticmethod
    def _parent_dir(path: str) -> str:
        if "/" not in path:
            return ""
        return path.rsplit("/", 1)[0]
