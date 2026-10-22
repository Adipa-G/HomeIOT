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

    def ticks_diff(self, a, b):
        return a - b

    def ticks_add(self, ticks, delta):
        return ticks + delta

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


class _SequencePresence:
    """Returns a different metadata dict for each heartbeat call."""

    def __init__(self, sequence):
        self._sequence = list(sequence)
        self.calls = 0

    def heartbeat_with_metadata(self):
        idx = min(self.calls, len(self._sequence) - 1)
        self.calls += 1
        return self._sequence[idx]


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
    def __init__(self, connected=True, fail_connect=False, power_save_result=True):
        super().__init__(connected=connected, fail_connect=fail_connect)
        self.power_modes = []
        self.power_save_result = power_save_result

    def set_power_save(self, mode):
        self.power_modes.append(mode)
        return self.power_save_result

    def get_power_save_modes(self):
        return {"none": 0, "modem": 1}


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
        self.prefetch_calls = 0
        self.prefetch_payloads = []

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

    def prefetch_server_code(self, modules):
        self.prefetch_calls += 1
        self.prefetch_payloads.append(modules)
        return True


class _FakeModuleRuntime:
    def __init__(self):
        self.update_calls = 0
        self.tick_calls = 0

    def update_assignment(self, *_args, **_kwargs):
        self.update_calls += 1

    def tick(self, **_kwargs):
        self.tick_calls += 1
        return {"reset_requested": False}

    def get_upcoming_modules(self, next_wake_ms=0):
        return []


class _FakeLogger:
    def __init__(self):
        self.info_calls = 0
        self.warn_calls = 0
        self.tick_calls = 0
        self.info_log = []

    def info(self, msg, data=None, **_kwargs):
        self.info_calls += 1
        self.info_log.append((msg, data))

    def warn(self, *_args, **_kwargs):
        self.warn_calls += 1

    def tick(self):
        self.tick_calls += 1


class _FakeUpdater:
    def __init__(self, update_info=None, check_error=None, apply_error=None):
        self.update_info = update_info
        self.check_error = check_error
        self.apply_error = apply_error
        self.check_calls = 0
        self.apply_calls = 0

    def check(self):
        self.check_calls += 1
        if self.check_error is not None:
            raise self.check_error
        return self.update_info

    def apply(self, update_info):
        self.apply_calls += 1
        if self.apply_error is not None:
            raise self.apply_error


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
        ota_poll_interval_ms=3600000,
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
    # Each iteration feeds at loop start and before sleeping; the first
    # iteration also feeds after its heartbeat and module-assignment calls.
    assert watchdog.feed_calls == 8
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
        system=_FakeSystem(),
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
        system=_FakeSystem(),
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
        system=_FakeSystem(),
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
        system=_FakeSystem(),
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
        system=_FakeSystem(),
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
        system=_FakeSystem(),
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


def test_requested_legacy_light_mode_maps_to_wifi_powersave():
    config = _config()
    config.power.wifi_power_save_enabled = True
    config.power.wifi_power_save_production_mode = "light"

    assert _requested_network_power_mode(config, "production") == "powersave"


def test_control_loop_warns_when_wifi_power_mode_is_rejected():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 1000})
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()
    network = _FakePowerNetwork(power_save_result=False)
    config = _config()
    config.power.wifi_power_save_enabled = True

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=config,
        network=network,
        max_iterations=1,
    )

    assert logger.warn_calls == 1
    assert not any(message == "WiFi power mode accepted" for message, _ in logger.info_log)


def test_control_loop_does_not_assume_legacy_none_means_power_mode_accepted():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 1000})
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()
    network = _FakePowerNetwork(power_save_result=None)
    config = _config()
    config.power.wifi_power_save_enabled = True

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=config,
        network=network,
        max_iterations=1,
    )

    assert logger.warn_calls == 1
    assert not any(message == "WiFi power mode accepted" for message, _ in logger.info_log)


def test_control_loop_reports_sleep_and_wifi_power_capabilities():
    class _CapabilitySystem(_FakeSystem):
        def get_sleep_capabilities(self):
            return {"lightsleep": True, "deepsleep": False}

    system = _CapabilitySystem()
    logger = _FakeLogger()
    network = _FakePowerNetwork()

    run_control_loop(
        system=system,
        presence=_FakePresence({"mode": "production"}),
        device_control=_FakeDeviceControl(),
        module_runtime=_FakeModuleRuntime(),
        logger=logger,
        config=_config(),
        network=network,
        max_iterations=0,
    )

    assert ("CPU sleep capabilities", {"lightsleep": True, "deepsleep": False}) in logger.info_log
    assert ("WiFi power-save modes", {"modes": ["modem", "none"]}) in logger.info_log


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


def test_mode_switches_on_first_heartbeat_returning_new_mode():
    """Mode must update immediately on the heartbeat that returns the new mode,
    not on the following one.  The 'Heartbeat sent' log should already reflect
    the new mode, and a 'Mode changed' log should be emitted exactly once."""
    system = _FakeSystem()
    presence = _SequencePresence([
        {"mode": "production", "next_heartbeat_ms": 1000, "module_assignment_poll_interval_ms": 60000},
        {"mode": "development", "next_heartbeat_ms": 1000, "dev_poll_interval_ms": 2000, "module_assignment_poll_interval_ms": 60000},
        {"mode": "development", "next_heartbeat_ms": 1000, "dev_poll_interval_ms": 2000, "module_assignment_poll_interval_ms": 60000},
    ])
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
        max_iterations=30,
    )

    heartbeat_logs = [(msg, d) for msg, d in logger.info_log if msg == "Heartbeat sent"]
    mode_change_logs = [(msg, d) for msg, d in logger.info_log if msg == "Mode changed"]

    # First heartbeat returns "production" → log says "production"
    assert heartbeat_logs[0][1]["mode"] == "production"
    # Second heartbeat returns "development" → log must say "development" immediately
    assert heartbeat_logs[1][1]["mode"] == "development"
    # A single "Mode changed" log is emitted
    assert len(mode_change_logs) == 1
    assert mode_change_logs[0][1] == {"from": "production", "to": "development"}


def test_prefetch_uses_next_actual_loop_wake_when_sleep_is_clamped():
    system = _FakeSystem()
    presence = _FakePresence(
        {
            "mode": "production",
            "next_heartbeat_ms": 200,
            "module_assignment_poll_interval_ms": 60000,
        }
    )
    device_control = _FakeDeviceControl(assignment=None)
    logger = _FakeLogger()

    class _RuntimeWithImminentModule(_FakeModuleRuntime):
        def get_upcoming_modules(self, next_wake_ms=0):
            # Simulate a module due at 550ms.
            # With now=100ms and production min sleep=500ms, next loop wake is 600ms,
            # so this should be prefetched.
            return [{"module_id": "temp-reader", "version": "1.0.0"}] if next_wake_ms >= 550 else []

    module_runtime = _RuntimeWithImminentModule()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        max_iterations=1,
    )

    assert device_control.prefetch_calls == 1
    assert device_control.prefetch_payloads[0][0]["module_id"] == "temp-reader"


def test_prefetch_logs_warning_when_server_rejects_request():
    system = _FakeSystem()
    presence = _FakePresence(
        {
            "mode": "production",
            "next_heartbeat_ms": 200,
            "module_assignment_poll_interval_ms": 60000,
        }
    )
    logger = _FakeLogger()

    class _DeviceControlRejectingPrefetch(_FakeDeviceControl):
        def prefetch_server_code(self, modules):
            self.prefetch_calls += 1
            self.prefetch_payloads.append(modules)
            return False

    class _RuntimeWithImminentModule(_FakeModuleRuntime):
        def get_upcoming_modules(self, next_wake_ms=0):
            return [{"module_id": "temp-reader", "version": "1.0.0"}] if next_wake_ms >= 550 else []

    device_control = _DeviceControlRejectingPrefetch(assignment=None)
    module_runtime = _RuntimeWithImminentModule()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        max_iterations=1,
    )

    assert device_control.prefetch_calls == 1
    assert logger.warn_calls >= 1


def test_prefetch_uses_heartbeat_horizon_in_development_mode():
    system = _FakeSystem()
    presence = _FakePresence(
        {
            "mode": "development",
            "next_heartbeat_ms": 30000,
            "dev_poll_interval_ms": 2000,
            "module_assignment_poll_interval_ms": 60000,
        }
    )
    device_control = _FakeDeviceControl(assignment=None)
    logger = _FakeLogger()

    class _RuntimeDueBeforeHeartbeat(_FakeModuleRuntime):
        def get_upcoming_modules(self, next_wake_ms=0):
            # With now=100ms, development next loop wake is typically ~150ms
            # (clamped by development min sleep), which is too short.
            # Using heartbeat horizon (~30100ms) should include this module.
            return [{"module_id": "temp-reader", "version": "1.0.0"}] if next_wake_ms >= 5000 else []

    module_runtime = _RuntimeDueBeforeHeartbeat()

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=_config(),
        max_iterations=1,
    )

    assert device_control.prefetch_calls == 1
    assert device_control.prefetch_payloads[0][0]["module_id"] == "temp-reader"


# OTA polling tests
def test_control_loop_skips_ota_check_when_updater_is_none():
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
        updater=None,
        max_iterations=3,
    )

    # Should run normally without errors
    assert module_runtime.tick_calls == 3
    assert logger.warn_calls == 0


def test_control_loop_performs_ota_check_at_interval():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 30000})
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()
    config = _config()
    config.ota_poll_interval_ms = 5000
    updater = _FakeUpdater(update_info=None)

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=config,
        updater=updater,
        max_iterations=50,
    )

    # OTA check should be called (at least once)
    assert updater.check_calls >= 1


def test_control_loop_applies_ota_update_when_available():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 30000})
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()
    config = _config()
    config.ota_poll_interval_ms = 5000

    class _UpdateInfo:
        version = "2.0.0"

    updater = _FakeUpdater(update_info=_UpdateInfo())

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=config,
        updater=updater,
        max_iterations=50,
    )

    assert updater.check_calls >= 1
    assert updater.apply_calls == 1
    assert any("OTA update available" in msg for msg, _ in logger.info_log)


def test_control_loop_handles_ota_check_exception_and_continues():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 30000})
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()
    config = _config()
    config.ota_poll_interval_ms = 5000
    updater = _FakeUpdater(check_error=RuntimeError("ota api unavailable"))

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=config,
        updater=updater,
        max_iterations=50,
    )

    assert updater.check_calls >= 1
    assert updater.apply_calls == 0
    assert logger.warn_calls >= 1
    assert module_runtime.tick_calls == 50


def test_control_loop_handles_ota_apply_exception_and_continues():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 30000})
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()
    config = _config()
    config.ota_poll_interval_ms = 5000

    class _UpdateInfo:
        version = "2.0.0"

    updater = _FakeUpdater(update_info=_UpdateInfo(), apply_error=RuntimeError("ota apply failed"))

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=config,
        updater=updater,
        max_iterations=50,
    )

    assert updater.check_calls >= 1
    assert updater.apply_calls == 1
    assert logger.warn_calls >= 1
    assert module_runtime.tick_calls == 50


def test_control_loop_does_not_check_ota_when_network_disconnected():
    system = _FakeSystem()
    presence = _FakePresence({"mode": "production", "next_heartbeat_ms": 30000})
    device_control = _FakeDeviceControl(assignment=None)
    module_runtime = _FakeModuleRuntime()
    logger = _FakeLogger()
    network = _FakeNetwork(connected=False, fail_connect=True)
    config = _config()
    config.ota_poll_interval_ms = 5000
    updater = _FakeUpdater(update_info=None)

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=config,
        network=network,
        updater=updater,
        max_iterations=20,
    )

    # When network is disconnected and stays disconnected, OTA check should not run
    assert updater.check_calls == 0



# Radio-off light sleep tests


class _ClockSystem(_FakeSystem):
    """Time advances only while sleeping, so sleep durations are exact."""

    def __init__(self, light_sleep_effective=True, early_wake_ms=None):
        super().__init__()
        self.light_sleep_calls = []
        self.light_sleep_effective = light_sleep_effective
        self.early_wake_ms = early_wake_ms

    def time_ms(self):
        return self._time_ms

    def sleep_ms(self, milliseconds):
        self.sleep_calls.append(milliseconds)
        self._time_ms += milliseconds

    def light_sleep_ms(self, milliseconds):
        self.light_sleep_calls.append(milliseconds)
        if self.early_wake_ms is not None:
            self._time_ms += self.early_wake_ms
            self.early_wake_ms = None
        elif self.light_sleep_effective:
            self._time_ms += milliseconds
        return True


class _SuspendableNetwork(_FakePowerNetwork):
    def __init__(self, suspend_error=None, **kwargs):
        super().__init__(**kwargs)
        self.suspend_calls = 0
        self.suspend_error = suspend_error

    def suspend(self):
        self.suspend_calls += 1
        if self.suspend_error is not None:
            raise self.suspend_error
        self.connected = False


class _ChunkWatchdog(_FakeWatchdog):
    def __init__(self, interval_ms):
        super().__init__()
        self.interval_ms = interval_ms

    def get_feed_interval_ms(self):
        return self.interval_ms


class _RecordingLogger(_FakeLogger):
    def __init__(self):
        super().__init__()
        self.warn_log = []

    def warn(self, msg, data=None, **_kwargs):
        self.warn_calls += 1
        self.warn_log.append((msg, data))


def _radio_off_config():
    cfg = _config_60s()
    cfg.power.wifi_power_save_production_mode = "powersave"
    cfg.power.radio_off_sleep_enabled = True
    cfg.power.radio_off_sleep_min_ms = 15000
    return cfg


def _run_radio_off(system, network, config=None, presence=None, watchdog=None, logger=None, iterations=3, module_runtime=None):
    logger = logger or _RecordingLogger()
    run_control_loop(
        system=system,
        presence=presence or _FakePresence({"mode": "production", "next_heartbeat_ms": 60000}),
        device_control=_FakeDeviceControl(assignment=None),
        module_runtime=module_runtime or _FakeModuleRuntime(),
        logger=logger,
        config=config or _radio_off_config(),
        network=network,
        watchdog=watchdog,
        max_iterations=iterations,
    )
    return logger


def test_radio_off_sleep_is_disabled_by_default():
    system = _ClockSystem()
    network = _SuspendableNetwork()

    _run_radio_off(system, network, config=_config_60s())

    assert network.suspend_calls == 0
    assert system.light_sleep_calls == []
    assert system.sleep_calls == [60000, 60000, 60000]


def test_radio_off_sleep_suspends_wifi_light_sleeps_and_reconnects():
    system = _ClockSystem()
    network = _SuspendableNetwork()

    logger = _run_radio_off(system, network)

    assert network.suspend_calls == 3
    assert system.light_sleep_calls == [60000, 60000, 60000]
    assert system.sleep_calls == []
    # Reconnects immediately after each wake, without waiting for retry backoff.
    assert network.connect_calls == 2
    # Power-save mode is re-applied after every radio power-up.
    assert network.power_modes == ["powersave", "powersave", "powersave"]
    connected_logs = [data for message, data in logger.info_log if message == "WiFi connected"]
    assert len(connected_logs) == 2
    assert all("connect_ms" in data for data in connected_logs)


def test_radio_off_sleep_not_used_in_development_mode():
    system = _ClockSystem()
    network = _SuspendableNetwork()
    presence = _FakePresence({"mode": "development", "next_heartbeat_ms": 60000, "dev_poll_interval_ms": 2000})

    _run_radio_off(system, network, presence=presence, iterations=5)

    assert network.suspend_calls == 0
    assert system.light_sleep_calls == []
    assert all(ms <= 1000 for ms in system.sleep_calls)


def test_radio_off_sleep_not_used_below_min_sleep():
    system = _ClockSystem()
    network = _SuspendableNetwork()
    config = _config()
    config.power.radio_off_sleep_enabled = True
    config.power.radio_off_sleep_min_ms = 15000

    _run_radio_off(system, network, config=config, presence=_FakePresence({"mode": "production", "next_heartbeat_ms": 30000}))

    assert network.suspend_calls == 0
    assert system.light_sleep_calls == []
    assert all(ms <= 5000 for ms in system.sleep_calls)


def test_radio_off_sleep_disabled_when_lightsleep_unavailable():
    class _NoLightSleepSystem(_ClockSystem):
        def get_sleep_capabilities(self):
            return {"lightsleep": False, "deepsleep": False}

    system = _NoLightSleepSystem()
    network = _SuspendableNetwork()

    logger = _run_radio_off(system, network, iterations=2)

    assert network.suspend_calls == 0
    assert system.sleep_calls == [60000, 60000]
    assert any("no machine.lightsleep" in message for message, _ in logger.warn_log)


def test_radio_off_sleep_disabled_when_network_has_no_suspend():
    system = _ClockSystem()
    network = _FakePowerNetwork()

    logger = _run_radio_off(system, network, iterations=2)

    assert system.light_sleep_calls == []
    assert system.sleep_calls == [60000, 60000]
    assert any("unsupported by HAL" in message for message, _ in logger.warn_log)


def test_radio_off_sleep_disabled_after_suspend_failure():
    system = _ClockSystem()
    network = _SuspendableNetwork(suspend_error=RuntimeError("wlan busy"))

    logger = _run_radio_off(system, network, iterations=3)

    assert network.suspend_calls == 1
    assert system.light_sleep_calls == []
    assert system.sleep_calls == [60000, 60000, 60000]
    assert any(message.startswith("WiFi suspend failed") for message, _ in logger.warn_log)


def test_radio_off_sleep_disabled_after_repeated_ineffective_light_sleep():
    system = _ClockSystem(light_sleep_effective=False)
    network = _SuspendableNetwork()

    logger = _run_radio_off(system, network, iterations=5)

    # Three failed cycles fall back to regular sleep, then the feature turns off.
    assert network.suspend_calls == 3
    assert system.light_sleep_calls == [60000, 60000, 60000]
    assert system.sleep_calls == [60000] * 5
    assert any(message.startswith("Light sleep is not sleeping") for message, _ in logger.warn_log)


def test_radio_off_light_sleep_resumes_after_early_wake():
    system = _ClockSystem(early_wake_ms=1000)
    network = _SuspendableNetwork()

    _run_radio_off(system, network, iterations=1)

    assert system.light_sleep_calls == [60000, 59000]
    assert system.sleep_calls == []


def test_radio_off_light_sleep_is_chunked_by_watchdog_feed_interval():
    system = _ClockSystem()
    network = _SuspendableNetwork()
    watchdog = _ChunkWatchdog(4000)

    _run_radio_off(system, network, watchdog=watchdog, iterations=1)

    assert system.light_sleep_calls == [4000] * 15
    # Loop start, heartbeat, module poll, pre-sleep, then one per light-sleep step.
    assert watchdog.feed_calls == 4 + 15


def test_regular_sleep_is_chunked_by_watchdog_feed_interval():
    system = _ClockSystem()
    watchdog = _ChunkWatchdog(4000)

    _run_radio_off(system, None, config=_config_60s(), watchdog=watchdog, iterations=1)

    assert system.sleep_calls == [4000] * 15
    # Loop start, heartbeat, module poll, pre-sleep, then between the 15 chunks.
    assert watchdog.feed_calls == 4 + 14


def test_regular_sleep_is_not_chunked_without_feed_interval():
    system = _ClockSystem()

    _run_radio_off(system, None, config=_config_60s(), watchdog=_ChunkWatchdog(None), iterations=1)

    assert system.sleep_calls == [60000]


def test_sleep_wakes_for_next_module_due_time():
    class _RuntimeWithDueModule(_FakeModuleRuntime):
        def get_next_due_ms(self):
            return 2000

    system = _ClockSystem()

    _run_radio_off(
        system,
        None,
        config=_config(),
        presence=_FakePresence({"mode": "production", "next_heartbeat_ms": 30000}),
        module_runtime=_RuntimeWithDueModule(),
        iterations=1,
    )

    assert system.sleep_calls == [2000]