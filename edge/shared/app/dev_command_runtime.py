def execute_dev_command(system, device_control, command, logger=None, utc_now_iso=None):
    utc_now = utc_now_iso or _default_utc_now_iso

    command_id = command.get("command_id")
    if not command_id:
        _log_warn(logger, "Dev command missing command_id", {"command": command})
        return {"status": "error", "reported": False}

    start_ms = system.time_ms()
    started_at_utc = utc_now()

    status = "success"
    exit_code = 0
    stdout_text = ""
    stderr_text = ""

    stdout_lines = []

    def _capture_print(*args, **kwargs):  # noqa: ARG001
        stdout_lines.append(" ".join(str(value) for value in args))

    code = str(command.get("code") or "")
    scope = {"print": _capture_print}
    try:
        try:
            exec(code, scope, scope)  # noqa: S102
        except SyntaxError:
            # Bare `return` at the top level causes SyntaxError in exec.
            # Wrap in a function so `return` works; capture the return value.
            wrapped = "def _dev_cmd_fn(ctx):\n" + "\n".join("    " + line for line in code.splitlines())
            exec(wrapped, scope, scope)  # noqa: S102
            return_val = scope["_dev_cmd_fn"](scope)
            if return_val is not None and "result" not in scope:
                scope["result"] = return_val
        # If code defines a `run` function but never calls it (the common pattern),
        # call it automatically and capture the return value.
        if "result" not in scope and callable(scope.get("run")):
            return_val = scope["run"](scope)
            if return_val is not None:
                scope["result"] = return_val
    except Exception as exc:
        status = "error"
        exit_code = 1
        stderr_text = _format_exception(exc)

    stdout_text = "\n".join(stdout_lines)
    data = _extract_result(scope)

    finish_ms = system.time_ms()
    finished_at_utc = utc_now()
    elapsed_ms = max(0, finish_ms - start_ms)

    timeout_ms = int(command.get("timeout_ms") or 0)
    if status == "success" and timeout_ms > 0 and elapsed_ms > timeout_ms:
        status = "timeout"
        exit_code = 124
        stderr_text = (
            "Dev command timeout exceeded: command_id="
            + str(command_id)
            + ", elapsed_ms="
            + str(elapsed_ms)
            + ", timeout_ms="
            + str(timeout_ms)
        )

    payload = {
        "command_id": command_id,
        "revision_hash": command.get("revision_hash"),
        "dedupe_token": command.get("dedupe_token"),
        "status": status,
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "elapsed_ms": elapsed_ms,
        "exit_code": exit_code,
        "stdout": _truncate(stdout_text, 4000),
        "stderr": _truncate(stderr_text, 4000),
        "data": data,
    }

    reported = False
    try:
        reported = device_control.report_dev_command_result(command_id, payload)
    except Exception as exc:
        _log_warn(
            logger,
            "Dev command result upload threw exception",
            {"command_id": command_id, "error": str(exc)},
        )
        reported = False

    if not reported:
        _log_warn(
            logger,
            "Dev command result upload failed",
            {"command_id": command_id, "status": status},
        )

    return {"status": status, "reported": reported, "payload": payload}


def _format_exception(exc):
    try:
        import traceback

        details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    except Exception:
        details = str(exc)
    return _truncate(details, 4000)


def _truncate(text, max_len):
    value = text or ""
    if len(value) <= max_len:
        return value
    return value[:max_len] + "..."


def _extract_result(scope):
    if "result" not in scope:
        return None
    value = scope["result"]
    # Accept dicts, lists, strings, numbers, booleans, None as-is.
    if isinstance(value, (dict, list, str, int, float, bool, type(None))):
        return value
    # Fallback: coerce to string so the payload is always serialisable.
    return str(value)


def _default_utc_now_iso():
    try:
        import time

        parts = time.gmtime()
        return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (
            parts[0],
            parts[1],
            parts[2],
            parts[3],
            parts[4],
            parts[5],
        )
    except Exception:
        return "1970-01-01T00:00:00Z"


def _log_warn(logger, message, context=None):
    if logger is not None:
        logger.warn(message, context)