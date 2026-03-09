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

        self._buffer = []
        self._buffer_bytes = 0
        self._dropped_count = 0
        self._drop_mode_bytes_remaining = 0
        self._last_flush_ms = self._system.time_ms()

    def info(self, message, context=None):
        self._log("INFO", message, context)

    def warn(self, message, context=None):
        self._log("WARN", message, context)

    def error(self, message, context=None):
        self._log("ERROR", message, context)

    def tick(self):
        now = self._system.time_ms()
        if now - self._last_flush_ms >= self._cfg.flush_interval_ms:
            self.flush("interval")

    def flush(self, reason="manual") -> bool:
        self._last_flush_ms = self._system.time_ms()

        if not self._cfg.enabled_uplink:
            return False
        if self._http is None or not self._api_url:
            return False
        if not self._buffer and self._dropped_count == 0:
            return False

        payload = {
            "device_id": self._device_id,
            "reason": reason,
            "sentAt": self._system.time_ms(),
            "dropped_count": self._dropped_count,
            "truncated": self._dropped_count > 0,
            "logs": list(self._buffer),
        }

        url = self._api_url + LOGS_PATH
        headers = {
            "X-Device-ID": self._device_id,
            "X-Api-Key": self._api_key,
        }
        response = self._http.post(url, payload, headers=headers)
        if response.status_code not in (200, 201):
            return False

        self._buffer = []
        self._buffer_bytes = 0
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

        event_bytes = self._event_size(event)

        if self._drop_mode_bytes_remaining > 0:
            self._drop_mode_bytes_remaining = max(0, self._drop_mode_bytes_remaining - event_bytes)
            self._dropped_count += 1
            return

        if self._buffer_bytes + event_bytes > self._cfg.buffer_max_bytes:
            flushed = False
            if self._buffer:
                flushed = self.flush("threshold")

            if flushed and self._buffer_bytes + event_bytes <= self._cfg.buffer_max_bytes:
                self._buffer.append(event)
                self._buffer_bytes += event_bytes
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
                )
            )
            return

        self._buffer.append(event)
        self._buffer_bytes += event_bytes

        if self._buffer_bytes >= self._cfg.buffer_max_bytes:
            self.flush("threshold")

    def _should_log(self, level):
        configured = _LEVELS.get(self._cfg.min_level.upper(), _LEVELS["INFO"])
        current = _LEVELS.get(level, _LEVELS["INFO"])
        return current >= configured

    @staticmethod
    def _format_console_event(event):
        context = event.get("context") or {}
        ctx = ""
        if context:
            ctx = " | " + json.dumps(context, separators=(",", ":"), sort_keys=True)
        return "[{ts}] {level} {message}{ctx}".format(
            ts=event.get("ts"),
            level=event.get("level"),
            message=event.get("message"),
            ctx=ctx,
        )

    @staticmethod
    def _event_size(event):
        return len(json.dumps(event, separators=(",", ":")).encode("utf-8"))
