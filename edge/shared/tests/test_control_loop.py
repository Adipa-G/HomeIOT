from edge.shared.app.config import Config
from edge.shared.app.control_loop import run_control_loop


class _FakeSystem:
    def __init__(self):
        self._time_ms = 0
        self.sleep_calls = []

    def time_ms(self):
        self._time_ms += 100
        return self._time_ms

    def sleep_ms(self, milliseconds):
        self.sleep_calls.append(milliseconds)


class _FakePresence:
    def __init__(self, metadata, error=None):
        self.metadata = metadata
        self.error = error
        self.calls = 0

    def heartbeat_with_metadata(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.metadata


class _FakeNetwork:
    def __init__(self, connected=True, fail_connect=False):
        self.connected = connected
        self.fail_connect = fail_connect
        self.connect_calls = 0

    def connect(self, _ssid, _password, timeout_ms=15000):
        self.connect_calls += 1
        if self.fail_connect:
            raise RuntimeError("wifi down")
        self.connected = True

    def is_connected(self):
        return self.connected

    def get_ip(self):
        return "192.168.1.20"


class _FakeWatchdog:
    def __init__(self):
        self.feed_calls = 0

    def feed(self):
        self.feed_calls += 1


class _FakeDeviceControl:
    def __init__(self, assignment=None, command=None, assignment_error=None, dev_error=None):
        self.assignment = assignment
        self.command = command
        self.assignment_error = assignment_error
        self.dev_error = dev_error
        self.assignment_calls = 0
        self.dev_calls = 0
        self.ensure_calls = 0

    def get_module_assignment(self, _):
        self.assignment_calls += 1
        if self.assignment_error is not None:
            raise self.assignment_error
        return self.assignment

    def ensure_assigned_modules_present(self, _):
        self.ensure_calls += 1
        return {"checked": 0, "ready": 0}

    def get_next_dev_command(self, _):
        self.dev_calls += 1
        if self.dev_error is not None:
            raise self.dev_error
        return self.command

    @staticmethod
    def should_execute_dev_command(command, _):
        return bool(command)


class _FakeModuleRuntime:
    def __init__(self):
        self.update_calls = 0
        self.tick_calls = 0

    def update_assignment(self, *_args, **_kwargs):
        self.update_calls += 1

    def tick(self, **_kwargs):
        self.tick_calls += 1
        return {"reset_requested": False}


class _FakeLogger:
    def __init__(self):
        self.info_calls = 0
        self.warn_calls = 0
        self.tick_calls = 0

    def info(self, *_args, **_kwargs):
        self.info_calls += 1

    def warn(self, *_args, **_kwargs):
        self.warn_calls += 1

    def tick(self):
        self.tick_calls += 1


def _config():
    return Config(
        device_id="esp32-001",
        api_url="http://localhost:8000",
        api_key="secret",
        wifi_ssid="ssid",
        wifi_password="pass",
        heartbeat_interval_ms=30000,
        max_boot_attempts=3,
        dev_poll_interval_ms=2000,
        module_assignment_poll_interval_ms=60000,
        current_version="1.0.0",
    )


def test_control_loop_production_does_not_spin_on_dev_timer():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 30000})
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        max_iterations=3,
    )

    assert all(ms >= 1000 for ms in system.sleep_calls)
    assert device_control.dev_calls == 0


def test_control_loop_development_polls_dev_more_frequently_than_heartbeat():
    system = _FakeSystem()
    presence = _FakePresence(
        {
            "mode": "development",
            "next_heartbeat_ms": 30000,
            "dev_poll_interval_ms": 2000,
            "module_assignment_poll_interval_ms": 60000,
        }
    )
    device_control = _FakeDeviceControl(assignment=None, command={"command_id": "cmd-1", "revision_hash": "r1"})
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        max_iterations=25,
    )

    assert device_control.dev_calls >= 1
    assert presence.calls <= 2


def test_control_loop_updates_runtime_when_assignment_present():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 30000})
    device_control = _FakeDeviceControl(assignment={"assignment_hash": "a1", "modules": []})
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        max_iterations=2,
    )

    assert device_control.assignment_calls >= 1
    assert device_control.ensure_calls == 1
    assert module_runtime.update_calls == 1


def test_control_loop_retries_network_and_feeds_watchdog():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 30000})
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()
    network = _FakeNetwork(connected=False)
    watchdog = _FakeWatchdog()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        network=network,
        watchdog=watchdog,
        max_iterations=3,
    )

    assert network.connect_calls >= 1
    assert watchdog.feed_calls == 3
    assert presence.calls >= 1


def test_control_loop_handles_heartbeat_exception_and_continues():
    system = _FakeSystem()
    presence = _FakePresence(None, error=RuntimeError("api unavailable"))
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        max_iterations=2,
    )

    assert logger.warn_calls >= 1
    assert module_runtime.tick_calls == 2


def test_control_loop_handles_assignment_poll_exception_and_continues():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 30000})
    device_control = _FakeDeviceControl(assignment_error=RuntimeError("assignment api unavailable"))
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        max_iterations=2,
    )

    assert device_control.assignment_calls >= 1
    assert logger.warn_calls >= 1
    assert module_runtime.tick_calls == 2


def test_control_loop_handles_dev_poll_exception_and_continues():
    system = _FakeSystem()
    presence = _FakePresence(
        {
            "mode": "development",
            "next_heartbeat_ms": 30000,
            "dev_poll_interval_ms": 2000,
            "module_assignment_poll_interval_ms": 60000,
        }
    )
    device_control = _FakeDeviceControl(dev_error=RuntimeError("dev api unavailable"))
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        max_iterations=3,
    )

    assert device_control.dev_calls >= 1
    assert logger.warn_calls >= 1
    assert module_runtime.tick_calls == 3


def test_control_loop_flushes_pending_module_status_when_connected():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 30000})
    device_control = _FakeDeviceControl(assignment=None)
    logger = _FakeLogger()
    network = _FakeNetwork(connected=True)

    flush_calls = []

    class _RuntimeWithFlush(_FakeModuleRuntime):
        def flush_pending_timeout_result(self):
            pass
        def flush_pending_module_status(self):
            flush_calls.append(1)

    module_runtime = _RuntimeWithFlush()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        network=network,
        max_iterations=3,
    )

    assert len(flush_calls) >= 3


def test_control_loop_handles_module_status_flush_exception_and_continues():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 30000})
    device_control = _FakeDeviceControl(assignment=None)
    logger = _FakeLogger()

    class _RuntimeWithBadFlush(_FakeModuleRuntime):
        def flush_pending_timeout_result(self):
            pass
        def flush_pending_module_status(self):
            raise RuntimeError("status api down")

    module_runtime = _RuntimeWithBadFlush()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        max_iterations=2,
    )

    assert logger.warn_calls >= 1
    assert module_runtime.tick_calls == 2
