import pytest
import json
from typing import Any

from edge.shared.app.config import Config
from edge.shared.app.module_runtime import ModuleRuntime
from edge.shared.app import startup
from edge.shared.app.startup import DeviceRuntime, create_runtime, run, run_device, start
from edge.shared.app.updater import Updater
from edge.shared.app.wall_clock import WallClock
from edge.shared.hal.interfaces import IFileSystem, ISystem
from edge.shared.tests.mocks.mock_filesystem import MockFileSystem
from edge.shared.tests.mocks.mock_http_client import MockHttpClient
from edge.shared.tests.mocks.mock_network import MockNetwork
from edge.shared.tests.mocks.mock_watchdog import MockWatchdog


def _config(wifi_country: str | None = None) -> Config:
    return Config(
        device_id="esp32-001",
        api_url="http://localhost:8000",
        api_key="secret",
        wifi_ssid="ssid",
        wifi_password="pass",
        heartbeat_interval_ms=30000,
        max_boot_attempts=3,
        current_version="1.0.0",
        wifi_country=wifi_country,
    )


class _FakeSystem(ISystem):
    def reset_cause(self) -> str:
        return "pwron_reset"

    def time_ms(self) -> int:
        return 0


class _FakeNetwork:
    def __init__(
        self, fail_connect: bool = False, connected: bool = True, country_ok: bool = True, hostname_ok: bool = True
    ):
        self.fail_connect = fail_connect
        self.connected = connected
        self.country_ok = country_ok
        self.hostname_ok = hostname_ok
        self.connect_calls: list[tuple[str, str]] = []
        self.country_calls: list[str] = []
        self.hostname_calls: list[str] = []

    def set_country(self, country: str) -> bool:
        self.country_calls.append(country)
        return self.country_ok

    def set_hostname(self, name: str) -> bool:
        self.hostname_calls.append(name)
        return self.hostname_ok

    def connect(self, ssid: str, password: str) -> None:
        self.connect_calls.append((ssid, password))
        if self.fail_connect:
            self.connected = False
            raise RuntimeError("wifi down")

    def is_connected(self) -> bool:
        return self.connected

    def get_ip(self) -> str:
        return "192.168.1.20"


class _FakeClock:
    def __init__(self, synced: bool = True):
        self.synced = synced
        self.sync_calls = 0

    def sync(self) -> bool:
        self.sync_calls += 1
        return self.synced


class _FakeWatchdog:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.feed_calls = 0

    def feed(self) -> None:
        self.feed_calls += 1
        if self.error is not None:
            raise self.error


class _FakeLogger:
    def __init__(self, events: list[str]):
        self.events = events
        self.infos: list[str] = []
        self.warns: list[str] = []

    def info(self, msg: str, data: object = None) -> None:
        self.infos.append(msg)

    def warn(self, msg: str, data: object = None) -> None:
        self.warns.append(msg)

    def flush(self, reason: str) -> None:
        self.events.append("flush:" + reason)


class _FakeBootManager:
    def __init__(self, events: list[str], state: dict[str, Any] | None = None):
        self.events = events
        self.state = state or {}

    def get_state(self) -> dict[str, Any]:
        return self.state

    def mark_success(self) -> None:
        self.events.append("mark_success")


class _FakePresence:
    def __init__(self, events: list[str], error: Exception | None = None):
        self.events = events
        self.error = error

    def register(self, version: str) -> bool:
        self.events.append("register:" + version)
        if self.error is not None:
            raise self.error
        return True


class _UpdateInfo:
    version = "2.0.0"


class _FakeUpdater:
    def __init__(
        self,
        events: list[str],
        update_info: _UpdateInfo | None = None,
        check_error: Exception | None = None,
        apply_error: Exception | None = None,
    ):
        self.events = events
        self.update_info = update_info
        self.check_error = check_error
        self.apply_error = apply_error

    def check(self) -> _UpdateInfo | None:
        self.events.append("ota_check")
        if self.check_error is not None:
            raise self.check_error
        return self.update_info

    def apply(self, update_info: _UpdateInfo) -> None:
        self.events.append("ota_apply:" + update_info.version)
        if self.apply_error is not None:
            raise self.apply_error


class _FakeModuleRuntime:
    def __init__(self, events: list[str], error: Exception | None = None):
        self.events = events
        self.error = error

    def flush_pending_timeout_result(self) -> None:
        self.events.append("flush_timeout")
        if self.error is not None:
            raise self.error

    def flush_pending_module_status(self) -> None:
        self.events.append("flush_status")
        if self.error is not None:
            raise self.error


_DEFAULT_UPDATER = object()


def _runtime(
    events: list[str],
    config: Config | None = None,
    network: _FakeNetwork | None = None,
    clock: _FakeClock | None = None,
    watchdog: _FakeWatchdog | None = None,
    boot_state: dict[str, Any] | None = None,
    presence_error: Exception | None = None,
    updater: object = _DEFAULT_UPDATER,
    module_error: Exception | None = None,
) -> Any:
    # Any: the runtime is built from fakes, and tests read their recorded state back through it.
    if updater is _DEFAULT_UPDATER:
        updater = _FakeUpdater(events)
    fakes: dict[str, Any] = dict(
        fs=object(),
        system=_FakeSystem(),
        http=object(),
        network=network or _FakeNetwork(),
        watchdog=watchdog or _FakeWatchdog(),
        config=config or _config(),
        logger=_FakeLogger(events),
        clock=clock or _FakeClock(),
        boot_manager=_FakeBootManager(events, boot_state),
        presence=_FakePresence(events, presence_error),
        updater=updater,
        device_control=object(),
        module_runtime=_FakeModuleRuntime(events, module_error),
    )
    return DeviceRuntime(**fakes)


# ---------------------------------------------------------------- create_runtime


def test_create_runtime_wires_shared_clock_into_module_runtime():
    runtime = create_runtime(
        fs=MockFileSystem(),
        system=_FakeSystem(),
        http=MockHttpClient(),
        network=MockNetwork(),
        watchdog=MockWatchdog(),
        config=_config(),
        platform="esp32",
    )

    assert isinstance(runtime.clock, WallClock)
    assert isinstance(runtime.module_runtime, ModuleRuntime)
    assert runtime.module_runtime._clock is runtime.clock


def test_create_runtime_builds_updater_for_platform_by_default():
    runtime = create_runtime(
        fs=MockFileSystem(),
        system=_FakeSystem(),
        http=MockHttpClient(),
        network=MockNetwork(),
        watchdog=MockWatchdog(),
        config=_config(),
        platform="pico",
    )

    assert isinstance(runtime.updater, Updater)
    assert runtime.updater._platform == "pico"


def test_create_runtime_omits_updater_when_ota_disabled():
    runtime = create_runtime(
        fs=MockFileSystem(),
        system=_FakeSystem(),
        http=MockHttpClient(),
        network=MockNetwork(),
        watchdog=MockWatchdog(),
        config=_config(),
        platform="simulator",
        enable_ota=False,
    )

    assert runtime.updater is None


# ---------------------------------------------------------------- start


def test_start_runs_boot_path_in_order_when_online():
    events: list[str] = []
    runtime = _runtime(events)

    start(runtime)

    assert events == [
        "register:1.0.0",
        "ota_check",
        "flush_timeout",
        "flush_status",
        "mark_success",
        "flush:startup",
    ]
    assert runtime.network.connect_calls == [("ssid", "pass")]
    assert runtime.clock.sync_calls == 1
    assert runtime.logger.warns == []


def test_start_uses_version_from_boot_state():
    events: list[str] = []
    runtime = _runtime(events, boot_state={"current_version": "1.4.2"})

    start(runtime)

    assert runtime.config.current_version == "1.4.2"
    assert "register:1.4.2" in events


def test_start_applies_available_update():
    events: list[str] = []
    runtime = _runtime(events)
    runtime.updater = _FakeUpdater(events, update_info=_UpdateInfo())

    start(runtime)

    assert events.index("ota_apply:2.0.0") == events.index("ota_check") + 1


def test_start_skips_ota_when_updater_disabled():
    events: list[str] = []
    runtime = _runtime(events, updater=None)

    start(runtime)

    assert not any(e.startswith("ota_") for e in events)
    assert "OTA updates disabled; skipping update check" in runtime.logger.infos
    assert events[-2:] == ["mark_success", "flush:startup"]


def test_start_continues_offline_when_wifi_connect_fails():
    events: list[str] = []
    runtime = _runtime(events, network=_FakeNetwork(fail_connect=True))

    start(runtime)

    assert events == ["mark_success", "flush:startup"]
    assert runtime.clock.sync_calls == 0
    assert "WiFi connection failed; continuing in offline mode" in runtime.logger.warns
    assert "Skipping registration and OTA check while offline" in runtime.logger.warns


def test_start_survives_service_exceptions_and_still_marks_success():
    events: list[str] = []
    runtime = _runtime(
        events,
        presence_error=RuntimeError("register boom"),
        updater=_FakeUpdater(events, update_info=_UpdateInfo(), apply_error=RuntimeError("apply boom")),
        module_error=RuntimeError("flush boom"),
        watchdog=_FakeWatchdog(error=RuntimeError("wdt boom")),
    )

    start(runtime)

    assert events[-2:] == ["mark_success", "flush:startup"]
    assert runtime.logger.warns == [
        "Device registration threw exception",
        "OTA apply threw exception",
        "Timeout marker flush threw exception",
        "Module-status marker flush threw exception",
    ]


def test_start_survives_ota_check_exception():
    events: list[str] = []
    runtime = _runtime(events)
    runtime.updater = _FakeUpdater(events, check_error=RuntimeError("check boom"))

    start(runtime)

    assert "OTA check threw exception" in runtime.logger.warns
    assert "mark_success" in events
    assert runtime.ota_checked is False


def test_start_records_completed_ota_check_even_when_apply_fails():
    events: list[str] = []
    runtime = _runtime(
        events,
        updater=_FakeUpdater([], update_info=_UpdateInfo(), apply_error=RuntimeError("ENOSPC")),
    )

    start(runtime)

    assert runtime.ota_checked is True


def test_start_leaves_ota_unchecked_when_offline_or_disabled():
    offline = _runtime([], network=_FakeNetwork(fail_connect=True))
    disabled = _runtime([], updater=None)

    start(offline)
    start(disabled)

    assert offline.ota_checked is False
    assert disabled.ota_checked is False


def test_start_sets_wifi_country_and_hostname():
    events: list[str] = []
    runtime = _runtime(events, config=_config(wifi_country="AU"))

    start(runtime)

    assert runtime.network.country_calls == ["AU"]
    assert runtime.network.hostname_calls == ["esp32-001"]
    assert "WiFi country set" in runtime.logger.infos


def test_start_warns_when_wifi_country_and_hostname_rejected():
    events: list[str] = []
    network = _FakeNetwork(country_ok=False, hostname_ok=False)
    runtime = _runtime(events, config=_config(wifi_country="AU"), network=network)

    start(runtime)

    assert "WiFi country not applied" in runtime.logger.warns
    assert "WiFi hostname not applied" in runtime.logger.warns


def test_start_skips_wifi_country_when_not_configured():
    events: list[str] = []
    config = _config()
    config.wifi_country = ""
    runtime = _runtime(events, config=config)

    start(runtime)

    assert runtime.network.country_calls == []


def test_start_warns_when_ntp_sync_fails():
    events: list[str] = []
    runtime = _runtime(events, clock=_FakeClock(synced=False))

    start(runtime)

    assert "NTP time sync failed; timestamps may be inaccurate" in runtime.logger.warns


# ---------------------------------------------------------------- run


def test_run_passes_runtime_services_to_control_loop(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Any] = {}

    def _run_control_loop(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("edge.shared.app.startup.run_control_loop", _run_control_loop)
    events: list[str] = []
    runtime = _runtime(events)

    run(runtime, max_iterations=5)

    assert captured == {
        "system": runtime.system,
        "presence": runtime.presence,
        "device_control": runtime.device_control,
        "module_runtime": runtime.module_runtime,
        "logger": runtime.logger,
        "config": runtime.config,
        "network": runtime.network,
        "watchdog": runtime.watchdog,
        "updater": runtime.updater,
        "max_iterations": 5,
        "clock": runtime.clock,
        "ota_checked": runtime.ota_checked,
    }


# ---------------------------------------------------------------- run_device


class _ConfigFs(IFileSystem):
    def __init__(self, files: dict[str, str]):
        self.files = files

    def read_text(self, path: str) -> str:
        return self.files[path]


def test_run_device_loads_config_then_starts_and_runs_with_ota_enabled(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, Any]] = []

    def _start(runtime: Any) -> None:
        calls.append(("start", runtime))

    def _run(runtime: Any) -> None:
        calls.append(("run", runtime))

    monkeypatch.setattr(startup, "start", _start)
    monkeypatch.setattr(startup, "run", _run)
    fs = _ConfigFs(
        {
            "config.json": json.dumps(
                {
                    "device_id": "pico-007",
                    "api_url": "http://api:5228/",
                    "api_key": "key",
                    "wifi_ssid": "ssid",
                    "wifi_password": "pass",
                    "heartbeat_interval_ms": 30000,
                    "max_boot_attempts": 3,
                }
            )
        }
    )

    run_device(
        fs=fs,
        system=_FakeSystem(),
        http=MockHttpClient(),
        network=MockNetwork(),
        watchdog=MockWatchdog(),
        platform="pico",
    )

    assert [name for name, _ in calls] == ["start", "run"]
    runtime = calls[0][1]
    assert calls[1][1] is runtime
    assert runtime.config.device_id == "pico-007"
    assert runtime.config.api_url == "http://api:5228"
    assert isinstance(runtime.updater, Updater)
    assert runtime.updater._platform == "pico"