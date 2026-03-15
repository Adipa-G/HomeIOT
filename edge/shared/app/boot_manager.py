import json

from edge.shared.app.config import CONFIG_PATH, CONFIG_PREV_PATH, CONFIG_STAGING_PATH
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
        config_path: str = CONFIG_PATH,
        config_prev_path: str = CONFIG_PREV_PATH,
        config_staging_path: str = CONFIG_STAGING_PATH,
        logger=None,
    ):
        self._fs = fs
        self._system = system
        self._max_attempts = max_attempts
        self._state_path = state_path
        self._app_path = app_path
        self._app_prev_path = app_prev_path
        self._app_staging_path = app_staging_path
        self._config_path = config_path
        self._config_prev_path = config_prev_path
        self._config_staging_path = config_staging_path
        self._logger = logger

    def on_boot(self):
        state = self._load_state()
        state["boot_count"] += 1
        state["boot_succeeded"] = False
        self._save_state(state)
        self._log_info(
            "Boot counter incremented",
            {"boot_count": state["boot_count"], "max_attempts": self._max_attempts},
        )

        if state["boot_count"] > self._max_attempts:
            if state.get("pending_app_changed") or state.get("pending_config_changed"):
                self.rollback()
            else:
                state["boot_count"] = 0
                state["boot_succeeded"] = False
                self._save_state(state)
                self._log_warn(
                    "Boot counter reset without rollback target",
                    {"boot_count": state["boot_count"], "max_attempts": self._max_attempts},
                )

        return state

    def get_state(self):
        return self._load_state()

    def mark_success(self) -> None:
        state = self._load_state()
        state["boot_count"] = 0
        state["boot_succeeded"] = True
        state["pending_app_changed"] = False
        state["pending_config_changed"] = False
        self._save_state(state)
        self._log_info("Boot marked successful")

    def set_new_version(self, version: str) -> None:
        state = self._load_state()
        self._log_info("Applying new version", {"version": version})

        app_staged = self._fs.exists(self._app_staging_path)
        config_staged = self._fs.exists(self._config_staging_path)

        if app_staged:
            self._remove_tree(self._app_prev_path)
            if self._fs.exists(self._app_path):
                self._copy_tree(self._app_path, self._app_prev_path)
            self._remove_tree(self._app_path)
            self._copy_tree(self._app_staging_path, self._app_path)

        self._promote_config()

        if app_staged:
            state["previous_version"] = state.get("current_version")
            state["current_version"] = version
        if config_staged:
            state["previous_config_version"] = state.get("config_version")
            state["config_version"] = version
        state["boot_count"] = 0
        state["boot_succeeded"] = False
        state["pending_app_changed"] = app_staged
        state["pending_config_changed"] = config_staged
        self._save_state(state)

        if app_staged:
            self._remove_tree(self._app_staging_path)
        self._remove_tree(self._config_staging_path)
        self._log_info("New version staged as active", {"version": version})

    def rollback(self) -> None:
        state = self._load_state()
        pending_app_changed = bool(state.get("pending_app_changed", False))
        pending_config_changed = bool(state.get("pending_config_changed", False))
        has_app_backup = self._fs.exists(self._app_prev_path)
        has_config_backup = self._fs.exists(self._config_prev_path)
        if pending_app_changed and not has_app_backup:
            raise RuntimeError("Rollback requested but app backup is missing")
        if pending_config_changed and not has_config_backup:
            raise RuntimeError("Rollback requested but config backup is missing")
        if not pending_app_changed and not pending_config_changed:
            raise RuntimeError("Rollback requested but no pending update is recorded")
        if not has_app_backup and not has_config_backup:
            raise RuntimeError("Rollback requested but no backup is available")
        self._log_warn("Rollback triggered", {"current_version": state.get("current_version")})

        if pending_app_changed:
            self._remove_tree(self._app_path)
            self._copy_tree(self._app_prev_path, self._app_path)

        if pending_config_changed:
            self._restore_config()

        if pending_app_changed:
            state["current_version"] = state.get("previous_version") or state.get("current_version")
        if pending_config_changed:
            state["config_version"] = state.get("previous_config_version") or state.get("config_version") or state["current_version"]
        state["boot_count"] = 0
        state["boot_succeeded"] = False
        state["pending_app_changed"] = False
        state["pending_config_changed"] = False
        self._save_state(state)
        self._system.reset()

    def _log_info(self, message: str, context=None) -> None:
        if self._logger is not None:
            self._logger.info(message, context)

    def _log_warn(self, message: str, context=None) -> None:
        if self._logger is not None:
            self._logger.warn(message, context)

    def _load_state(self):
        if not self._fs.exists(self._state_path):
            default_state = {
                "boot_count": 0,
                "boot_succeeded": False,
                "current_version": "0.0.0",
                "previous_version": None,
                "config_version": "0.0.0",
                "previous_config_version": None,
                "pending_app_changed": False,
                "pending_config_changed": False,
            }
            self._save_state(default_state)
            return default_state

        state = json.loads(self._fs.read_text(self._state_path))
        defaults = {
            "boot_count": 0,
            "boot_succeeded": False,
            "current_version": "0.0.0",
            "previous_version": None,
            "config_version": "0.0.0",
            "previous_config_version": None,
            "pending_app_changed": False,
            "pending_config_changed": False,
        }
        changed = False
        for key, value in defaults.items():
            if key not in state:
                state[key] = value
                changed = True
        if changed:
            self._save_state(state)
        return state

    def _save_state(self, state) -> None:
        atomic_write_text(self._fs, self._state_path, json.dumps(state))

    def _promote_config(self) -> None:
        if not self._fs.exists(self._config_staging_path):
            return

        self._remove_tree(self._config_prev_path)
        if self._fs.exists(self._config_path):
            self._copy_tree(self._config_path, self._config_prev_path)

        self._remove_tree(self._config_path)
        self._copy_tree(self._config_staging_path, self._config_path)

    def _restore_config(self) -> None:
        if not self._fs.exists(self._config_prev_path):
            return

        self._remove_tree(self._config_path)
        self._copy_tree(self._config_prev_path, self._config_path)

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
