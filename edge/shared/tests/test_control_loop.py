from edge.shared.app.config import Config
from edge.shared.app.control_loop import (
    _ensure_network_connected,
    _requested_network_power_mode,
    run_control_loop,
)


class _FakeSystem:
    def __init__(self):
        self._time_ms = 0
        self.sleep_calls = []

    def time_ms(self):
        self._time_ms += 100
        return self._time_ms

    def uptime_ms(self):
        return self._time_ms

    def free_memory_bytes(self):
        return 65536

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


class _FakePowerNetwork(_FakeNetwork):
    def __init__(self, connected=True, fail_connect=False):
        super().__init__(connected=connected, fail_connect=fail_connect)
        self.power_modes = []

    def set_power_save(self, mode):
        self.power_modes.append(mode)


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


def test_control_loop_uses_longer_idle_sleep_in_production_mode():
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

    assert all(ms >= 500 for ms in system.sleep_calls)


def test_control_loop_applies_exponential_reconnect_backoff_when_wifi_down():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 30000})
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()
    network = _FakeNetwork(connected=False, fail_connect=True)

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        network=network,
        max_iterations=120,
    )

    # With now advancing by 100ms per loop, 120 loops reaches 12s:
    # retries should occur at ~0s and ~5s (next at ~15s is out of range).
    assert network.connect_calls == 2


def test_ensure_network_connected_backoff_sequence_and_cap():
    class _StaticConfig:
        wifi_ssid = "ssid"
        wifi_password = "pass"

    logger = _FakeLogger()
    network = _FakeNetwork(connected=False, fail_connect=True)

    state = _ensure_network_connected(
        network=network,
        config=_StaticConfig(),
        logger=logger,
        now_ms=0,
        next_retry_ms=0,
        retry_interval_ms=5000,
        retry_base_ms=5000,
        retry_max_ms=60000,
    )
    assert state["connected"] is False
    assert state["next_retry_ms"] == 5000
    assert state["retry_interval_ms"] == 10000

    state = _ensure_network_connected(
        network=network,
        config=_StaticConfig(),
        logger=logger,
        now_ms=5000,
        next_retry_ms=5000,
        retry_interval_ms=10000,
        retry_base_ms=5000,
        retry_max_ms=60000,
    )
    assert state["next_retry_ms"] == 15000
    assert state["retry_interval_ms"] == 20000

    state = _ensure_network_connected(
        network=network,
        config=_StaticConfig(),
        logger=logger,
        now_ms=15000,
        next_retry_ms=15000,
        retry_interval_ms=20000,
        retry_base_ms=5000,
        retry_max_ms=60000,
    )
    assert state["next_retry_ms"] == 35000
    assert state["retry_interval_ms"] == 40000

    state = _ensure_network_connected(
        network=network,
        config=_StaticConfig(),
        logger=logger,
        now_ms=35000,
        next_retry_ms=35000,
        retry_interval_ms=40000,
        retry_base_ms=5000,
        retry_max_ms=60000,
    )
    assert state["next_retry_ms"] == 75000
    assert state["retry_interval_ms"] == 60000

    state = _ensure_network_connected(
        network=network,
        config=_StaticConfig(),
        logger=logger,
        now_ms=36000,
        next_retry_ms=75000,
        retry_interval_ms=60000,
        retry_base_ms=5000,
        retry_max_ms=60000,
    )
    assert state["next_retry_ms"] == 75000
    assert state["retry_interval_ms"] == 60000


def test_ensure_network_connected_resets_retry_interval_after_success():
    class _StaticConfig:
        wifi_ssid = "ssid"
        wifi_password = "pass"

    logger = _FakeLogger()
    network = _FakeNetwork(connected=False, fail_connect=False)

    state = _ensure_network_connected(
        network=network,
        config=_StaticConfig(),
        logger=logger,
        now_ms=10000,
        next_retry_ms=10000,
        retry_interval_ms=60000,
        retry_base_ms=5000,
        retry_max_ms=60000,
    )

    assert state["connected"] is True
    assert state["next_retry_ms"] == 10000
    assert state["retry_interval_ms"] == 5000


def test_control_loop_applies_wifi_power_modes_by_mode_when_enabled():
    system = _FakeSystem()
    presence = _FakePresence(
        {
            "mode": "production",
            "next_heartbeat_ms": 1000,
            "dev_poll_interval_ms": 2000,
            "module_assignment_poll_interval_ms": 60000,
        }
    )
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()
    network = _FakePowerNetwork(connected=True)
    config = _config()
    config.power.wifi_power_save_enabled = True
    config.power.wifi_power_save_production_mode = "modem"

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=config,
        network=network,
        max_iterations=3,
    )

    assert network.power_modes == ["modem"]


def test_requested_network_power_mode_uses_development_override():
    config = _config()
    config.power.wifi_power_save_enabled = True
    config.power.wifi_power_save_production_mode = "modem"
    config.power.wifi_power_save_development_mode = "none"

    assert _requested_network_power_mode(config, "production") == "modem"
    assert _requested_network_power_mode(config, "development") == "none"


def _config_60s():
    from edge.shared.app.config import PowerConfig
    cfg = _config()
    cfg.heartbeat_interval_ms = 60000
    cfg.power = PowerConfig(
        enabled=True,
        production_sleep_min_ms=60000,
        production_sleep_max_ms=60000,
        development_sleep_min_ms=50,
        development_sleep_max_ms=1000,
        network_retry_base_ms=5000,
        network_retry_max_ms=60000,
        wifi_power_save_enabled=True,
        wifi_power_save_production_mode="modem",
        wifi_power_save_development_mode="none",
    )
    return cfg


def test_production_60s_cadence_sleep_is_exactly_60000():
    """Production loop should sleep exactly 60s when all timers are aligned."""
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 60000})
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config_60s(),
        max_iterations=3,
    )

    # After first heartbeat the scheduler should reach ~60000ms sleep.
    # System advances by 100ms per call so only first iteration fires immediately;
    # subsequent ones must wait full window — all sleeps should be 60000ms.
    assert all(ms == 60000 for ms in system.sleep_calls[1:])


def test_development_mode_sleep_remains_short_with_60s_config():
    """Switching to development keeps sleep under 1000ms regardless of 60s power config."""
    system = _FakeSystem()
    presence = _FakePresence(
        {
            "mode": "development",
            "next_heartbeat_ms": 60000,
            "dev_poll_interval_ms": 2000,
            "module_assignment_poll_interval_ms": 60000,
        }
    )
    device_control = _FakeDeviceControl(
        assignment=None,
        command={"command_id": "cmd-1", "revision_hash": "r1"},
    )
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config_60s(),
        max_iterations=10,
    )

    assert all(ms <= 1000 for ms in system.sleep_calls)
    assert device_control.dev_calls >= 1


def test_production_mode_does_not_poll_dev_commands_with_60s_config():
    """Production mode must not touch the dev command endpoint, even with 60s config."""
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 60000})
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config_60s(),
        max_iterations=5,
    )

    assert device_control.dev_calls == 0
