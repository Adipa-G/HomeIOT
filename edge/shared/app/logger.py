import json

from edge.shared.app.endpoints import LOGS_PATH
from edge.shared.app.config import LoggingConfig


_LEVELS = {"INFO": 20, "WARN": 30, "ERROR": 40}


class EdgeLogger:
    def __init__(
        self,
        system,
        http=None,
        device_id="unknown",
        api_url="",
        api_key="",
        logging_config=None,
    ):
        self._system = system
        self._http = http
        self._device_id = device_id
        self._api_url = api_url.rstrip("/") if api_url else ""
        self._api_key = api_key
        self._cfg = logging_config or LoggingConfig(enabled_uplink=False)

        self._buffer_data = bytearray()
        self._entry_count = 0
        self._dropped_count = 0
        self._drop_mode_bytes_remaining = 0
        self._last_flush_ms = self._system.time_ms()
        self._uplink_paused = False

    def pause_uplink(self):
        """Temporarily suppress uplink flushes (e.g. during OTA)."""
        self._uplink_paused = True

    def resume_uplink(self):
        """Re-enable uplink flushes after pausing."""
        self._uplink_paused = False

    def info(self, message, context=None):
        self._log("INFO", message, context)

    def warn(self, message, context=None):
        self._log("WARN", message, context)

    def error(self, message, context=None):
        self._log("ERROR", message, context)

    def tick(self):
        now = self._system.time_ms()
        if self._system.ticks_diff(now, self._last_flush_ms) >= self._cfg.flush_interval_ms:
            self.flush("interval")

    def flush(self, reason="manual") -> bool:
        self._last_flush_ms = self._system.time_ms()

        if self._uplink_paused:
            return False
        if not self._cfg.enabled_uplink:
            return False
        if self._http is None or not self._api_url:
            return False
        if not self._buffer_data and self._dropped_count == 0:
            return False

        logs = self._decode_buffer()

        payload = {
            "device_id": self._device_id,
            "reason": reason,
            "sentAt": self._system.time_ms(),
            "dropped_count": self._dropped_count,
            "truncated": self._dropped_count > 0,
            "logs": logs,
        }

        url = self._api_url + LOGS_PATH
        headers = {
            "X-Device-ID": self._device_id,
            "X-Api-Key": self._api_key,
        }
        # Console-level info about dispatch (does not enqueue into the uplink buffer)
        try:
            console_event = {
                "ts": self._system.time_ms(),
                "level": "INFO",
                "message": "Sending log batch",
                "context": {"url": url, "reason": reason, "count": len(logs), "dropped_count": self._dropped_count},
            }
            print(self._format_console_event(console_event))
        except Exception:
            # Fail silently; logging should not break normal flow
            pass
        try:
            response = self._http.post(url, payload, headers=headers, timeout_s=self._cfg.flush_timeout_s)
        except Exception:
            return False
        if response.status_code not in (200, 201):
            return False

        self._buffer_data = bytearray()
        self._entry_count = 0
        self._dropped_count = 0
        return True

    def _log(self, level, message, context=None):
        if not self._should_log(level):
            return

        event = {
            "ts": self._system.time_ms(),
            "level": level,
            "message": message,
            "context": context or {},
        }

        # Console logging is always enabled and never writes to filesystem.
        print(self._format_console_event(event))

        if not self._cfg.enabled_uplink:
            return

        event_line = json.dumps(event)
        event_bytes = len(event_line) + 1  # +1 for newline separator

        if self._drop_mode_bytes_remaining > 0:
            self._drop_mode_bytes_remaining = max(0, self._drop_mode_bytes_remaining - event_bytes)
            self._dropped_count += 1
            return

        if len(self._buffer_data) + event_bytes > self._cfg.buffer_max_bytes:
            flushed = False
            if self._buffer_data:
                flushed = self.flush("threshold")

            if flushed and len(self._buffer_data) + event_bytes <= self._cfg.buffer_max_bytes:
                self._buffer_data.extend(event_line.encode("utf-8"))
                self._buffer_data.extend(b"\n")
                self._entry_count += 1
                return

            self._dropped_count += 1
            self._drop_mode_bytes_remaining = max(256, self._cfg.buffer_max_bytes // 8)
            print(
                self._format_console_event(
                    {
                        "ts": self._system.time_ms(),
                        "level": "WARN",
                        "message": "Log buffer full; truncating newest logs",
                        "context": {
                            "buffer_max_bytes": self._cfg.buffer_max_bytes,
                            "dropped_count": self._dropped_count,
                        },
                    }
                ),
            )
            return

        self._buffer_data.extend(event_line.encode("utf-8"))
        self._buffer_data.extend(b"\n")
        self._entry_count += 1

        if len(self._buffer_data) >= self._cfg.buffer_max_bytes:
            self.flush("threshold")

    def _should_log(self, level):
        configured = _LEVELS.get(self._cfg.min_level.upper(), _LEVELS["INFO"])
        current = _LEVELS.get(level, _LEVELS["INFO"])
        return current >= configured

    def _decode_buffer(self):
        if not self._buffer_data:
            return []
        raw = bytes(self._buffer_data).decode("utf-8")
        return [json.loads(line) for line in raw.strip().split("\n") if line]

    @staticmethod
    def _format_console_event(event):
        context = event.get("context") or {}
        ctx = ""
        if context:
            ctx = " | " + json.dumps(context)
        return "[{ts}] {level} {message}{ctx}".format(
            ts=event.get("ts"),
            level=event.get("level"),
            message=event.get("message"),
            ctx=ctx,
        )


