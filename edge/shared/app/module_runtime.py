from dataclasses import dataclass
import json

from edge.shared.app.safe_io import atomic_write_text


@dataclass
class ModuleSchedule:
    module_id: str
    version: str
    interval_ms: int
    timeout_ms: int
    entrypoint: str = "run"
    next_due_ms: int = 0
    run_seq: int = 0


class ModuleRuntime:
    def __init__(
        self,
        system,
        device_control,
        config,
        fs=None,
        logger=None,
        utc_now_iso=None,
        timeout_marker_path="module_timeout_pending.json",
        pending_module_status_path="module_status_pending.json",
        quarantine_root="modules_cache",
        quarantine_threshold=3,
    ):
        self._system = system
        self._device_control = device_control
        self._config = config
        self._fs = fs
        self._logger = logger
        self._utc_now_iso = utc_now_iso or self._default_utc_now_iso
        self._timeout_marker_path = timeout_marker_path
        self._pending_module_status_path = pending_module_status_path
        self._quarantine_root = quarantine_root
        self._quarantine_threshold = quarantine_threshold
        self._modules = {}

    def flush_pending_timeout_result(self):
        payload = self._load_timeout_marker()
        if not payload:
            return False
        uploaded = self._report_result(payload)
        if uploaded:
            self._clear_timeout_marker()
            self._log_info(
                "Pending timeout result uploaded",
                {"module_id": payload.get("module_id"), "run_id": payload.get("run_id")},
            )
            return True
        return False

    def flush_pending_module_status(self):
        payload = self._load_module_status_marker()
        if not payload:
            return False
        try:
            ok = self._device_control.report_module_status(payload)
        except Exception:
            ok = False
        if ok:
            self._clear_module_status_marker()
            self._log_info(
                "Pending module-status notification uploaded",
                {"module_id": payload.get("module_id")},
            )
            return True
        return False

    def update_assignment(self, assignment_payload, now_ms=None):
        now = self._system.time_ms() if now_ms is None else now_ms
        incoming = self._extract_modules(assignment_payload)

        next_state = {}
        for item in incoming:
            module_id = str(item.get("module_id", "")).strip()
            version = str(item.get("version", "")).strip()
            if not module_id or not version:
                continue

            interval_ms = max(1000, int(item.get("interval_ms", 60000)))
            timeout_ms = max(1, int(item.get("timeout_ms", 10000)))
            entrypoint = str(item.get("entrypoint", "run"))

            # Load quarantine before version check so enabled=True re-enable can see the previous disabled state.
            q_current = self._load_quarantine(module_id)

            previous = self._modules.get(module_id)
            if previous and previous.version == version:
                next_due_ms = previous.next_due_ms
                run_seq = previous.run_seq
            else:
                next_due_ms = now
                run_seq = 0
                self._clear_quarantine(module_id)

            # Server can re-enable a disabled module by including enabled=True in the assignment.
            if item.get("enabled") is True and q_current.get("disabled"):
                self._clear_quarantine(module_id)
                next_due_ms = now
                self._ack_module_reenabled(module_id, version)

            next_state[module_id] = ModuleSchedule(
                module_id=module_id,
                version=version,
                interval_ms=interval_ms,
                timeout_ms=timeout_ms,
                entrypoint=entrypoint,
                next_due_ms=next_due_ms,
                run_seq=run_seq,
            )

        self._modules = next_state
        return {"assigned": len(self._modules)}

    def tick(self, now_ms=None):
        now = self._system.time_ms() if now_ms is None else now_ms
        executed = 0
        success = 0
        failed = 0

        for schedule in list(self._modules.values()):
            if now < schedule.next_due_ms:
                continue

            q = self._load_quarantine(schedule.module_id)
            if q.get("disabled"):
                schedule.next_due_ms = now + schedule.interval_ms
                continue

            executed += 1
            outcome = self._run_one(schedule)
            if outcome["status"] == "success":
                success += 1
            else:
                failed += 1

            schedule.next_due_ms = now + schedule.interval_ms

            if outcome["status"] == "timeout":
                return {
                    "executed": executed,
                    "success": success,
                    "failed": failed,
                    "reset_requested": True,
                }

        return {
            "executed": executed,
            "success": success,
            "failed": failed,
            "reset_requested": False,
        }

    def _run_one(self, schedule):
        start_ms = self._system.time_ms()
        start_utc = self._utc_now_iso()
        run_id = self._next_run_id(schedule, start_ms)

        # Increment failed_start_count before execution so the count survives a watchdog reset.
        q = self._load_quarantine(schedule.module_id)
        q["failed_start_count"] = q.get("failed_start_count", 0) + 1
        q["last_version"] = schedule.version
        q["last_run_id"] = run_id
        q["last_started_at_utc"] = start_utc
        self._save_quarantine(schedule.module_id, q)

        status = "success"
        output = {}
        error_message = None

        try:
            entrypoint = self._load_entrypoint(schedule)
            context = {
                "module_id": schedule.module_id,
                "module_version": schedule.version,
                "device_id": self._config.device_id,
                "run_id": run_id,
                "system": self._system,
            }
            returned = entrypoint(context)
            output = self._normalize_output(returned)
        except Exception as exc:
            status = "error"
            output = {}
            error_message = self._format_exception(exc)

        finish_ms = self._system.time_ms()
        finish_utc = self._utc_now_iso()
        elapsed_ms = max(0, finish_ms - start_ms)

        if status == "success" and elapsed_ms > schedule.timeout_ms:
            status = "timeout"
            output = {}
            error_message = (
                "Module timeout exceeded: module_id="
                + schedule.module_id
                + ", elapsed_ms="
                + str(elapsed_ms)
                + ", timeout_ms="
                + str(schedule.timeout_ms)
            )

        if status == "success":
            self._clear_quarantine(schedule.module_id)
        else:
            count = q["failed_start_count"]
            if count >= self._quarantine_threshold:
                disabled_reason = (
                    "Failed start count exceeded threshold ("
                    + str(count)
                    + " consecutive failure"
                    + ("s" if count != 1 else "")
                    + ")"
                )
                q["disabled"] = True
                q["disabled_reason"] = disabled_reason
                q["disabled_at_utc"] = finish_utc
                self._save_quarantine(schedule.module_id, q)
                self._log_warn(
                    "Module quarantined after repeated failures",
                    {"module_id": schedule.module_id, "failed_start_count": count},
                )
                status_payload = {
                    "device_id": self._config.device_id,
                    "module_id": schedule.module_id,
                    "module_version": schedule.version,
                    "disabled": True,
                    "disabled_reason": disabled_reason,
                    "failed_start_count": count,
                    "disabled_at_utc": finish_utc,
                }
                try:
                    ok = self._device_control.report_module_status(status_payload)
                except Exception:
                    ok = False
                if not ok:
                    self._persist_module_status_marker(status_payload)

        payload = {
            "device_id": self._config.device_id,
            "module_id": schedule.module_id,
            "module_version": schedule.version,
            "run_id": run_id,
            "started_at_utc": start_utc,
            "finished_at_utc": finish_utc,
            "elapsed_ms": elapsed_ms,
            "status": status,
            "output": output,
            "error_message": error_message,
        }

        if status == "timeout":
            self._persist_timeout_marker(payload)
            uploaded = self._report_result(payload)
            if uploaded:
                self._clear_timeout_marker()
            self._log_warn("Module timeout exceeded; resetting device", payload)
            self._system.reset()
        else:
            self._report_result(payload)

        if status == "error":
            self._log_warn("Module execution failed", payload)

        return {"status": status, "run_id": run_id}

    def _load_entrypoint(self, schedule):
        package = self._device_control.get_cached_module_package(schedule.module_id, schedule.version)
        if package is None:
            raise FileNotFoundError(
                "Module package not cached for " + schedule.module_id + "@" + schedule.version
            )
        source = package.decode("utf-8")
        scope = {}
        exec(source, scope, scope)
        entrypoint = scope.get(schedule.entrypoint)
        if not callable(entrypoint):
            raise ValueError(
                "Entrypoint not found or not callable: "
                + schedule.entrypoint
                + " in "
                + schedule.module_id
                + "@"
                + schedule.version
            )
        return entrypoint

    @staticmethod
    def _normalize_output(returned):
        if returned is None:
            return {}
        if isinstance(returned, dict):
            return returned
        return {"result": returned}

    def _next_run_id(self, schedule, start_ms):
        schedule.run_seq += 1
        return schedule.module_id + ":" + schedule.version + ":" + str(start_ms) + ":" + str(schedule.run_seq)

    @staticmethod
    def _extract_modules(assignment_payload):
        if not assignment_payload or not isinstance(assignment_payload, dict):
            return []
        if isinstance(assignment_payload.get("modules"), list):
            return assignment_payload.get("modules") or []
        if assignment_payload.get("module_id") and assignment_payload.get("version"):
            return [assignment_payload]
        return []

    @staticmethod
    def _default_utc_now_iso():
        try:
            import time
            parts = time.gmtime()
            return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (
                parts[0], parts[1], parts[2], parts[3], parts[4], parts[5],
            )
        except Exception:
            return "1970-01-01T00:00:00Z"

    @staticmethod
    def _format_exception(exc):
        try:
            import traceback
            details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        except Exception:
            details = str(exc)
        if len(details) > 2000:
            details = details[:2000] + "..."
        return details

    def _report_result(self, payload):
        try:
            ok = self._device_control.report_module_result(payload)
            if not ok:
                self._log_warn(
                    "Module result upload failed",
                    {
                        "module_id": payload.get("module_id"),
                        "module_version": payload.get("module_version"),
                        "run_id": payload.get("run_id"),
                        "status": payload.get("status"),
                    },
                )
                return False
            return True
        except Exception as exc:
            self._log_warn(
                "Module result upload threw exception",
                {
                    "module_id": payload.get("module_id"),
                    "module_version": payload.get("module_version"),
                    "run_id": payload.get("run_id"),
                    "error": str(exc),
                },
            )
            return False

    def _ack_module_reenabled(self, module_id, version):
        payload = {
            "device_id": self._config.device_id,
            "module_id": module_id,
            "module_version": version,
            "disabled": False,
        }
        try:
            self._device_control.report_module_status(payload)
        except Exception as exc:
            self._log_warn(
                "Failed to acknowledge module re-enable",
                {"module_id": module_id, "error": str(exc)},
            )

    # ------------------------------------------------------------------ quarantine state

    def _quarantine_path(self, module_id):
        return self._quarantine_root + "/" + str(module_id) + "/quarantine.json"

    def _load_quarantine(self, module_id):
        default = {
            "failed_start_count": 0,
            "disabled": False,
            "disabled_reason": None,
            "disabled_at_utc": None,
            "last_version": None,
        }
        if self._fs is None:
            return default
        path = self._quarantine_path(module_id)
        if not self._fs.exists(path):
            return default
        try:
            raw = self._fs.read_text(path)
            state = json.loads(raw)
            if isinstance(state, dict):
                return state
        except Exception as exc:
            self._log_warn("Failed to load quarantine state", {"module_id": module_id, "error": str(exc)})
        return default

    def _save_quarantine(self, module_id, state):
        if self._fs is None:
            return
        try:
            atomic_write_text(self._fs, self._quarantine_path(module_id), json.dumps(state))
        except Exception as exc:
            self._log_warn("Failed to persist quarantine state", {"module_id": module_id, "error": str(exc)})

    def _clear_quarantine(self, module_id):
        if self._fs is None:
            return
        path = self._quarantine_path(module_id)
        try:
            if self._fs.exists(path) and not self._fs.is_dir(path):
                self._fs.remove(path)
        except Exception as exc:
            self._log_warn("Failed to clear quarantine state", {"module_id": module_id, "error": str(exc)})

    # ------------------------------------------------------------------ pending module-status marker

    def _persist_module_status_marker(self, payload):
        if self._fs is None:
            return
        try:
            atomic_write_text(self._fs, self._pending_module_status_path, json.dumps(payload))
        except Exception as exc:
            self._log_warn("Failed to persist module-status marker", {"error": str(exc)})

    def _load_module_status_marker(self):
        if self._fs is None or not self._fs.exists(self._pending_module_status_path):
            return None
        try:
            raw = self._fs.read_text(self._pending_module_status_path)
            payload = json.loads(raw)
            if isinstance(payload, dict):
                return payload
        except Exception as exc:
            self._log_warn("Failed to load module-status marker", {"error": str(exc)})
        return None

    def _clear_module_status_marker(self):
        if self._fs is None:
            return
        try:
            if (
                self._fs.exists(self._pending_module_status_path)
                and not self._fs.is_dir(self._pending_module_status_path)
            ):
                self._fs.remove(self._pending_module_status_path)
        except Exception as exc:
            self._log_warn("Failed to clear module-status marker", {"error": str(exc)})

    # ------------------------------------------------------------------ timeout marker

    def _persist_timeout_marker(self, payload):
        if self._fs is None:
            return
        try:
            atomic_write_text(self._fs, self._timeout_marker_path, json.dumps(payload))
        except Exception as exc:
            self._log_warn("Failed to persist timeout marker", {"error": str(exc)})

    def _load_timeout_marker(self):
        if self._fs is None or not self._fs.exists(self._timeout_marker_path):
            return None
        try:
            raw = self._fs.read_text(self._timeout_marker_path)
            payload = json.loads(raw)
            if isinstance(payload, dict):
                return payload
        except Exception as exc:
            self._log_warn("Failed to load timeout marker", {"error": str(exc)})
        return None

    def _clear_timeout_marker(self):
        if self._fs is None:
            return
        try:
            if self._fs.exists(self._timeout_marker_path) and not self._fs.is_dir(self._timeout_marker_path):
                self._fs.remove(self._timeout_marker_path)
        except Exception as exc:
            self._log_warn("Failed to clear timeout marker", {"error": str(exc)})

    def _log_info(self, message, context=None):
        if self._logger is not None:
            self._logger.info(message, context)

    def _log_warn(self, message, context=None):
        if self._logger is not None:
            self._logger.warn(message, context)