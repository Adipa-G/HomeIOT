import json

from edge.shared.app.config import CONFIG_PATH, CONFIG_PREV_PATH, CONFIG_STAGING_PATH
from edge.shared.hal.interfaces import IFileSystem, ISystem
from edge.shared.app.safe_io import atomic_write_bytes, atomic_write_text

TYPE_CHECKING = False
if TYPE_CHECKING:  # never true on a device; see edge/shared/hal/interfaces.py
    from typing import Any

    from edge.shared.app.protocols import Logger

# OTA stages the root entry points (boot.py, main.py) in this folder inside the app
# tree. They are copied to the filesystem root only when the app is swapped, and the
# outgoing ones are saved in app_prev, so entry points always match the app version.
ROOT_FILES_DIR = "_root"


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
        logger: "Logger | None" = None,
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

    def on_boot(self) -> "dict[str, Any]":
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

    def get_state(self) -> "dict[str, Any]":
        return self._load_state()

    def discard_app_backup(self) -> bool:
        """Delete app_prev once the running app is confirmed, freeing flash for OTA staging.

        Rollback only restores app_prev while pending_app_changed is set, which
        mark_success() clears, so a confirmed app's backup can never be used.
        """
        if not self._fs.exists(self._app_prev_path):
            return False
        if self._load_state().get("pending_app_changed"):
            return False
        self._remove_tree(self._app_prev_path)
        self._log_info("Discarded confirmed app backup", {"path": self._app_prev_path})
        return True

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
            had_app = self._fs.exists(self._app_path)
            if had_app:
                self._fs.rename(self._app_path, self._app_prev_path)
            self._fs.rename(self._app_staging_path, self._app_path)
            if had_app:
                self._backup_root_files(self._app_prev_path)
            self._install_root_files(self._app_path)

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

        if not pending_app_changed and not pending_config_changed:
            raise RuntimeError("Rollback requested but no pending update is recorded")

        self._log_warn("Rollback triggered", {"current_version": state.get("current_version")})

        if pending_app_changed:
            if has_app_backup:
                self._remove_tree(self._app_path)
                self._fs.rename(self._app_prev_path, self._app_path)
                if not self._install_root_files(self._app_path):
                    self._log_warn("Restored app has no boot.py/main.py backup; keeping current entry points")
                state["current_version"] = state.get("previous_version") or state.get("current_version")
            else:
                # No backup exists (e.g. first OTA from a freshly-deployed device).
                # Cannot restore; keep current app and clear the pending flag so the
                # device can attempt to boot rather than looping forever.
                self._log_warn("App backup missing; cannot roll back app, keeping current version")

        if pending_config_changed:
            if has_config_backup:
                self._restore_config()
                state["config_version"] = state.get("previous_config_version") or state.get("config_version") or state["current_version"]
            else:
                self._log_warn("Config backup missing; cannot roll back config, keeping current config")

        state["boot_count"] = 0
        state["boot_succeeded"] = False
        state["pending_app_changed"] = False
        state["pending_config_changed"] = False
        self._save_state(state)
        self._system.reset()

    def _log_info(self, message: str, context: "dict[str, Any] | None" = None) -> None:
        if self._logger is not None:
            self._logger.info(message, context)

    def _log_warn(self, message: str, context: "dict[str, Any] | None" = None) -> None:
        if self._logger is not None:
            self._logger.warn(message, context)

    def _load_state(self) -> "dict[str, Any]":
        if not self._fs.exists(self._state_path):
            default_state: "dict[str, Any]" = {
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

        state: "dict[str, Any]" = json.loads(self._fs.read_text(self._state_path))
        defaults: "dict[str, Any]" = {
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

    def _save_state(self, state: "dict[str, Any]") -> None:
        atomic_write_text(self._fs, self._state_path, json.dumps(state))

    def _promote_config(self) -> None:
        if not self._fs.exists(self._config_staging_path):
            return

        self._remove_tree(self._config_prev_path)
        if self._fs.exists(self._config_path):
            self._fs.rename(self._config_path, self._config_prev_path)

        self._fs.rename(self._config_staging_path, self._config_path)

    def _restore_config(self) -> None:
        if not self._fs.exists(self._config_prev_path):
            return

        self._remove_tree(self._config_path)
        self._fs.rename(self._config_prev_path, self._config_path)

    def _backup_root_files(self, app_dir: str) -> None:
        """Save the live boot.py/main.py with the outgoing app so rollback can restore them."""
        backup_dir = self._join(app_dir, ROOT_FILES_DIR)
        for name in ("boot.py", "main.py"):
            if self._fs.exists(name):
                if not self._fs.exists(backup_dir):
                    self._fs.makedirs(backup_dir)
                atomic_write_bytes(self._fs, self._join(backup_dir, name), self._fs.read_bytes(name))

    def _install_root_files(self, app_dir: str) -> bool:
        """Copy the app's staged boot.py/main.py to the filesystem root. Returns False if it has none."""
        source_dir = self._join(app_dir, ROOT_FILES_DIR)
        if not self._fs.exists(source_dir):
            return False
        for name in self._fs.listdir(source_dir):
            atomic_write_bytes(self._fs, name, self._fs.read_bytes(self._join(source_dir, name)))
        return True

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

        if not self._fs.is_dir(path):
            self._fs.remove(path)
            return

        # Iterative depth-first removal.  The recursive version keeps
        # every parent's listdir() result alive on the call stack which
        # fragments the MicroPython heap on large trees.
        dirs = [path]
        idx = 0
        while idx < len(dirs):
            current = dirs[idx]
            for name in self._fs.listdir(current):
                child = self._join(current, name)
                if self._fs.is_dir(child):
                    dirs.append(child)
                else:
                    self._fs.remove(child)
            idx += 1
        # Remove directories deepest-first
        for i in range(len(dirs) - 1, -1, -1):
            self._fs.rmdir(dirs[i])

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
