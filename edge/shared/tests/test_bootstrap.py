import ast
import base64
import hashlib
import json
import os
import sys
from collections.abc import Sequence
from typing import IO, Any
from pathlib import Path

import pytest

from edge.bootstrap import loader
from edge.bootstrap.bootstrap import connect_wifi, run_bootstrap, write_config
from edge.bootstrap.provisioning import build_device_config
from edge.shared.app.config import Config
from edge.shared.app.secret_crypto import decrypt_secret
from edge.shared.hal.interfaces import HttpResponse
from edge.shared.tests.mocks.mock_filesystem import MockFileSystem
from edge.shared.tests.mocks.mock_http_client import MockHttpClient
from edge.shared.tests.mocks.mock_network import MockNetwork
from edge.shared.tests.mocks.mock_system import MockSystem
from edge.tools import build_artifact

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = json.loads((ROOT / "edge" / "bootstrap" / "bundle.json").read_text(encoding="utf-8"))
API_URL = "http://hub.local:5228"

TEMPLATE = {
    "device_id": "replace-with-device-id",
    "api_url": "replace-with-api-url",
    "api_key": "replace-with-device-api-key",
    "wifi_ssid": "replace-with-ssid",
    "wifi_password": "replace-with-password",
    "heartbeat_interval_ms": 60000,
    "max_boot_attempts": 3,
    "current_version": "0.0.0",
    "logging": {"enabled_uplink": True, "buffer_max_bytes": 4096, "flush_interval_ms": 60000, "min_level": "INFO"},
}


def _provision(**overrides: str) -> dict[str, str]:
    data = {
        "device_id": "esp32-new",
        "platform": "esp32",
        "api_url": API_URL + "/",
        "api_key": "generated-key",
        "wifi_ssid": "HomeWiFi",
        "wifi_password": "p@ss \"quoted\" ✓",
    }
    data.update(overrides)
    return data


def _release_source(rel_path: str, platform: str = "esp32") -> Path:
    return build_artifact._collect_files(ROOT, platform)[rel_path]


def _build_script(provision: dict[str, str], platform: str = "esp32") -> str:
    """Mirror of the API's BootstrapScriptBuilder output format."""
    lines = [(ROOT / BUNDLE["loader"]).read_text(encoding="utf-8").rstrip("\n"), ""]
    lines.append(loader.PROVISION_MARKER + json.dumps(provision, ensure_ascii=False))
    sources = [(p, ROOT / p) for p in BUNDLE["bootstrap_files"]]
    sources += [(p, _release_source(p, platform)) for p in BUNDLE["release_files"]]
    for rel_path, src in sources:
        lines.append(loader.FILE_MARKER + rel_path)
        for line in src.read_text(encoding="utf-8").splitlines():
            lines.append(loader.LINE_MARKER + line)
        lines.append(loader.END_MARKER)
    return "\n".join(lines) + "\n"


def _build_script_from_release(provision: dict[str, str], artifact_dir: Path) -> str:
    """Mirror of BootstrapScriptBuilder reading a built release: .py as text, else .mpy as base64."""
    lines = [(ROOT / BUNDLE["loader"]).read_text(encoding="utf-8").rstrip("\n"), ""]
    lines.append(loader.PROVISION_MARKER + json.dumps(provision, ensure_ascii=False))
    for rel_path in BUNDLE["bootstrap_files"]:
        lines.append(loader.FILE_MARKER + rel_path)
        lines += [loader.LINE_MARKER + line for line in (ROOT / rel_path).read_text(encoding="utf-8").splitlines()]
        lines.append(loader.END_MARKER)
    for rel_path in BUNDLE["release_files"]:
        source = artifact_dir / rel_path
        if source.exists():
            lines.append(loader.FILE_MARKER + rel_path)
            lines += [loader.LINE_MARKER + line for line in source.read_text(encoding="utf-8").splitlines()]
        else:
            compiled = rel_path[: -len(".py")] + ".mpy"
            data = (artifact_dir / compiled).read_bytes()
            lines.append(loader.BINARY_FILE_MARKER + compiled)
            lines += [loader.LINE_MARKER + base64.b64encode(data[i : i + 57]).decode() for i in range(0, len(data), 57)]
        lines.append(loader.END_MARKER)
    return "\n".join(lines) + "\n"


def _ota_stream(files: Sequence[tuple[str, bytes]]) -> bytes:
    out = bytearray()
    for rel_path, content in files:
        out.extend(("HASH:" + hashlib.sha256(content).hexdigest() + "\n").encode())
        out.extend(("FILE:" + rel_path + "\n").encode())
        out.extend(("SIZE:" + str(len(content)) + "\n").encode())
        out.extend(content)
    out.extend(b"END\n")
    return bytes(out)


def _release_files() -> list[tuple[str, bytes]]:
    return [
        ("boot.py", b"print('boot')\n"),
        ("main.py", b"print('firmware main')\n"),
        ("config.json", json.dumps(TEMPLATE).encode()),
        ("edge/shared/app/module.py", b"VALUE = 1\n"),
    ]


def _mock_ota(http: MockHttpClient, version: str = "1.2.0", files: Sequence[tuple[str, bytes]] | None = None) -> None:
    files = files if files is not None else _release_files()
    manifest = [{"path": p, "hash": hashlib.sha256(c).hexdigest()} for p, c in files]
    http.add_json_response(
        "GET",
        API_URL + "/api/ota/check?version=0.0.0",
        200,
        {"available": True, "version": version, "manifest": manifest},
    )
    http.add_stream_response(API_URL + "/api/ota/stream?version=" + version, _ota_stream(files))


class _SilentLogger:
    def __init__(self):
        self.messages: list[tuple[str, str]] = []

    def info(self, message: str, context: dict[str, Any] | None = None) -> None:
        self.messages.append(("INFO", message))

    def warn(self, message: str, context: dict[str, Any] | None = None) -> None:
        self.messages.append(("WARN", message))

    def error(self, message: str, context: dict[str, Any] | None = None) -> None:
        self.messages.append(("ERROR", message))

    def flush(self, reason: str | None = None) -> None:
        pass


# ---------------------------------------------------------------- provisioning


def test_build_device_config_encrypts_secrets_and_keeps_template_values():
    config = build_device_config(TEMPLATE, "dev-1", API_URL + "/", "key-1", "ssid", "pw")

    assert config["device_id"] == "dev-1"
    assert config["api_url"] == API_URL
    assert "api_key" not in config and "wifi_password" not in config
    assert decrypt_secret(config["api_key_enc"], "dev-1", "api_key") == "key-1"
    assert decrypt_secret(config["wifi_password_enc"], "dev-1", "wifi_password") == "pw"
    assert config["heartbeat_interval_ms"] == 60000
    assert config["max_boot_attempts"] == 3
    assert config["current_version"] == "0.0.0"
    assert config["security"]["binding"] == "device_id"
    assert TEMPLATE["api_key"] == "replace-with-device-api-key"


def test_build_device_config_applies_overrides_and_default_logging():
    template = dict(TEMPLATE)
    del template["logging"]

    config = build_device_config(
        template, "dev-1", API_URL, "k", "s", "p",
        current_version="2.0.0", heartbeat_interval_ms=1234, max_boot_attempts=7,
    )

    assert config["heartbeat_interval_ms"] == 1234
    assert config["max_boot_attempts"] == 7
    assert config["current_version"] == "2.0.0"
    assert config["logging"]["min_level"] == "INFO"


def test_write_config_rejects_missing_fields():
    provision = _provision()
    del provision["api_key"]

    with pytest.raises(ValueError, match="api_key"):
        write_config(MockFileSystem(), provision, TEMPLATE)


# ---------------------------------------------------------------- bundle.json


@pytest.mark.parametrize("platform", ["esp32", "pico"])
def test_bundle_release_files_are_part_of_every_release(platform: str):
    release = build_artifact._collect_files(ROOT, platform)

    missing = [p for p in BUNDLE["release_files"] if p not in release]

    assert missing == []


def test_bundle_bootstrap_files_exist_and_are_not_shipped_as_firmware():
    release = build_artifact._collect_files(ROOT, "esp32")

    for rel_path in BUNDLE["bootstrap_files"] + [BUNDLE["loader"]]:
        assert (ROOT / rel_path).is_file()
        assert rel_path not in release


def _is_type_checking_block(node: ast.AST) -> bool:
    return isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING"


def _runtime_nodes(tree: ast.AST):
    """Walk tree, skipping `if TYPE_CHECKING:` bodies (type-only imports never run)."""
    pending = [tree]
    while pending:
        node = pending.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if _is_type_checking_block(child):
                pending.extend(getattr(child, "orelse", []))
            else:
                pending.append(child)


def _edge_imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in _runtime_nodes(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("edge."):
            yield node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("edge."):
                    yield alias.name


def test_bundle_covers_bootstrap_import_closure():
    bundled = set(BUNDLE["bootstrap_files"]) | set(BUNDLE["release_files"])
    pending = ["edge.bootstrap.bootstrap"]
    seen: set[str] = set()
    while pending:
        module = pending.pop()
        if module in seen:
            continue
        seen.add(module)
        rel_path = module.replace(".", "/") + ".py"
        assert rel_path in bundled, module + " is imported by the bootstrap but missing from bundle.json"
        parts = module.split(".")
        for i in range(1, len(parts)):
            init = "/".join(parts[:i]) + "/__init__.py"
            assert init in bundled, init + " missing from bundle.json"
        pending.extend(_edge_imports(ROOT / rel_path))


# ---------------------------------------------------------------- loader


def _utf8_text_open(path: str, mode: str = "r") -> IO[Any]:
    # MicroPython always uses UTF-8; CPython on Windows would default to cp1252.
    return open(path, mode) if "b" in mode else open(path, mode, encoding="utf-8")


def test_extract_payload_writes_embedded_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    # MicroPython always uses UTF-8; CPython on Windows would default to cp1252.
    monkeypatch.setattr(loader, "open", _utf8_text_open, raising=False)
    provision = _provision()
    Path("main.py").write_text(_build_script(provision), encoding="utf-8")

    provision_json = loader.extract_payload(os)

    assert provision_json is not None
    assert json.loads(provision_json) == provision
    for rel_path in BUNDLE["release_files"]:
        extracted = (tmp_path / loader.LIB_DIR / rel_path).read_text(encoding="utf-8")
        assert extracted.splitlines() == _release_source(rel_path).read_text(encoding="utf-8").splitlines()
    for rel_path in BUNDLE["bootstrap_files"]:
        extracted = (tmp_path / loader.LIB_DIR / rel_path).read_text(encoding="utf-8")
        assert extracted.splitlines() == (ROOT / rel_path).read_text(encoding="utf-8").splitlines()


def test_generated_script_is_valid_python(tmp_path: Path):
    script = _build_script(_provision())

    compile(script, "main.py", "exec")


def test_extract_payload_replaces_stale_lib_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    stale = tmp_path / loader.LIB_DIR / "stale" / "old.py"
    stale.parent.mkdir(parents=True)
    stale.write_text("x = 1\n")
    Path("main.py").write_text("#@@FILE a/b.py\n#|y = 2\n#@@END\n", encoding="utf-8")

    assert loader.extract_payload(os) is None

    assert not stale.exists()
    assert (tmp_path / loader.LIB_DIR / "a" / "b.py").read_text() == "y = 2\n"


@pytest.mark.parametrize(
    "content, message",
    [
        ("#@@FILE ../evil.py\n#|x\n#@@END\n", "Unsafe"),
        ("#@@FILE a.py\n#|x\n", "missing end"),
        ("#@@FILE a.py\n#|x\nprint(1)\n#@@END\n", "unterminated"),
    ],
)
def test_extract_payload_rejects_corrupt_payloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str, message: str
):
    monkeypatch.chdir(tmp_path)
    Path("main.py").write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        loader.extract_payload(os)


def test_extract_payload_writes_compiled_release_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    artifact_dir = build_artifact.build("esp32", "1.0.0", tmp_path / "artifacts", compile_mpy=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(loader, "open", _utf8_text_open, raising=False)
    script = _build_script_from_release(_provision(), artifact_dir)
    Path("main.py").write_text(script, encoding="utf-8")
    compile(script, "main.py", "exec")

    loader.extract_payload(os)

    compiled = [p for p in BUNDLE["release_files"] if not (artifact_dir / p).exists()]
    assert {"mpy_probe.py", "edge/shared/app/updater.py", "edge/shared/app/boot_manager.py"} <= set(compiled)
    for rel_path in BUNDLE["release_files"]:
        if rel_path in compiled:
            shipped = rel_path[: -len(".py")] + ".mpy"
            assert (tmp_path / loader.LIB_DIR / shipped).read_bytes() == (artifact_dir / shipped).read_bytes()
        else:
            extracted = (tmp_path / loader.LIB_DIR / rel_path).read_text(encoding="utf-8")
            assert extracted.splitlines() == (artifact_dir / rel_path).read_text(encoding="utf-8").splitlines()


def _compiled_installer(provision: dict[str, str]) -> str:
    probe = base64.b64encode(b"M\x06\x00\x1f probe").decode()
    return "\n".join([
        loader.PROVISION_MARKER + json.dumps(provision),
        loader.BINARY_FILE_MARKER + "mpy_probe.mpy",
        loader.LINE_MARKER + probe,
        loader.END_MARKER,
        loader.FILE_MARKER + "config.json",
        loader.LINE_MARKER + json.dumps(TEMPLATE),
        loader.END_MARKER,
    ]) + "\n"


def test_loader_run_stops_before_install_when_probe_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))
    Path("main.py").write_text(_compiled_installer(_provision()), encoding="utf-8")
    calls: list[str] = []

    def failing_probe(lib_dir: str) -> None:
        calls.append(lib_dir)
        raise ValueError("This firmware can't load the installer's compiled modules")

    with pytest.raises(ValueError, match="can't load the installer's compiled modules"):
        loader.run(os_mod=os, services=(MockFileSystem(), MockSystem(), MockNetwork(), MockHttpClient()), probe=failing_probe)

    assert calls == [loader.LIB_DIR]
    assert (tmp_path / loader.LIB_DIR / "mpy_probe.mpy").read_bytes() == b"M\x06\x00\x1f probe"


def test_loader_run_skips_probe_for_source_installer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))
    Path("main.py").write_text(_build_script(_provision()), encoding="utf-8")
    fs, system, network, http = MockFileSystem(), MockSystem(), MockNetwork(), MockHttpClient()
    _mock_ota(http)
    calls: list[str] = []

    loader.run(os_mod=os, services=(fs, system, network, http), probe=calls.append)

    assert calls == []
    assert system.reset_calls == 1


def test_import_probe_explains_failure_and_cleans_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    (tmp_path / "mpy_probe.py").write_text("raise ValueError('incompatible .mpy file')\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"can't load the installer's compiled modules \(incompatible .mpy file\)"):
        loader.import_probe(str(tmp_path))

    assert "mpy_probe" not in sys.modules


def test_import_probe_accepts_loadable_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    (tmp_path / "mpy_probe.py").write_text("OK = 1\n", encoding="utf-8")

    loader.import_probe(str(tmp_path))

    assert "mpy_probe" not in sys.modules


def test_loader_run_installs_release_and_cleans_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))
    Path("main.py").write_text(_build_script(_provision()), encoding="utf-8")
    fs, system, network, http = MockFileSystem(), MockSystem(), MockNetwork(), MockHttpClient()
    _mock_ota(http)

    loader.run(os_mod=os, services=(fs, system, network, http))

    assert not (tmp_path / loader.LIB_DIR).exists()
    assert system.reset_calls == 1
    assert fs.read_text("main.py") == "print('firmware main')\n"


# ---------------------------------------------------------------- run_bootstrap


def test_run_bootstrap_writes_config_and_installs_latest_release():
    fs, system, network, http = MockFileSystem(), MockSystem(), MockNetwork(), MockHttpClient()
    _mock_ota(http, version="1.2.0")

    run_bootstrap(fs, system, network, http, _provision(), TEMPLATE, logger=_SilentLogger())

    assert network.connect_calls[0][:2] == ("HomeWiFi", "p@ss \"quoted\" ✓")
    check_call = http.calls[0]
    assert check_call[3]["X-Device-ID"] == "esp32-new"
    assert check_call[3]["X-Api-Key"] == "generated-key"
    assert check_call[3]["X-Platform"] == "esp32"
    assert fs.read_text("boot.py") == "print('boot')\n"
    assert fs.read_text("main.py") == "print('firmware main')\n"
    assert fs.exists("app/edge/shared/app/module.py")
    assert system.reset_calls == 1

    config = Config.load(fs, system=system)
    assert config.device_id == "esp32-new"
    assert config.api_url == API_URL
    assert config.api_key == "generated-key"
    assert config.wifi_password == "p@ss \"quoted\" ✓"
    assert config.current_version == "1.2.0"
    raw = json.loads(fs.read_text("config.json"))
    assert "api_key" not in raw and "wifi_password" not in raw

    state = json.loads(fs.read_text("boot_state.json"))
    assert state["current_version"] == "1.2.0"
    assert state["pending_app_changed"] is True


def test_run_bootstrap_raises_when_no_release_available():
    fs, system, network, http = MockFileSystem(), MockSystem(), MockNetwork(), MockHttpClient()
    http.add_json_response("GET", API_URL + "/api/ota/check?version=0.0.0", 200, {"available": False})

    with pytest.raises(RuntimeError, match="No firmware release"):
        run_bootstrap(fs, system, network, http, _provision(), TEMPLATE, logger=_SilentLogger())

    assert system.reset_calls == 0
    assert Config.load(fs, system=system).device_id == "esp32-new"


def test_run_bootstrap_raises_when_device_is_rejected():
    fs, system, network, http = MockFileSystem(), MockSystem(), MockNetwork(), MockHttpClient()
    http.add_json_response("GET", API_URL + "/api/ota/check?version=0.0.0", 401, {"error": "unauthorized"})

    with pytest.raises(RuntimeError, match="No firmware release"):
        run_bootstrap(fs, system, network, http, _provision(), TEMPLATE, logger=_SilentLogger())


class _FailingHttp(MockHttpClient):
    def __init__(self, error: Exception):
        super().__init__()
        self._error = error

    def get(self, url: str, headers: dict[str, str] | None = None) -> HttpResponse:
        raise self._error


@pytest.mark.parametrize("errno", [-2, -202])
def test_run_bootstrap_explains_unresolvable_api_host(errno: int):
    fs, system, network = MockFileSystem(), MockSystem(), MockNetwork()

    with pytest.raises(RuntimeError, match="Cannot resolve the API host in " + API_URL):
        run_bootstrap(fs, system, network, _FailingHttp(OSError(errno)), _provision(), TEMPLATE, logger=_SilentLogger())

    assert system.reset_calls == 0


def test_run_bootstrap_propagates_other_network_errors():
    fs, system, network = MockFileSystem(), MockSystem(), MockNetwork()

    with pytest.raises(OSError):
        run_bootstrap(fs, system, network, _FailingHttp(OSError(-113)), _provision(), TEMPLATE, logger=_SilentLogger())


class _FlakyNetwork(MockNetwork):
    def __init__(self, failures: int):
        super().__init__()
        self._failures = failures

    def connect(self, ssid: str, password: str, timeout_ms: int = 15000) -> None:
        self.connect_calls.append((ssid, password, timeout_ms))
        if len(self.connect_calls) <= self._failures:
            raise OSError("timeout")
        self.connected = True


def _loaded_config() -> Config:
    fs = MockFileSystem()
    write_config(fs, _provision(), TEMPLATE)
    return Config.load(fs)


def test_connect_wifi_retries_then_succeeds():
    network, system = _FlakyNetwork(failures=2), MockSystem()

    connect_wifi(network, system, _loaded_config(), _SilentLogger())

    assert len(network.connect_calls) == 3
    assert system.sleep_calls == [5000, 5000]


def test_connect_wifi_gives_up_after_attempts():
    network, system = _FlakyNetwork(failures=5), MockSystem()

    with pytest.raises(RuntimeError, match="WiFi"):
        connect_wifi(network, system, _loaded_config(), _SilentLogger())

    assert len(network.connect_calls) == 3


def test_connect_wifi_sets_country_before_connecting():
    class _CountryNetwork(MockNetwork):
        def __init__(self):
            super().__init__()
            self.events: list[tuple[str, str]] = []

        def set_country(self, country: str) -> bool:
            self.events.append(("country", country))
            return True

        def connect(self, ssid: str, password: str, timeout_ms: int = 15000) -> None:
            self.events.append(("connect", ssid))
            super().connect(ssid, password, timeout_ms)

    config = _loaded_config()
    config.wifi_country = "AU"
    network = _CountryNetwork()

    connect_wifi(network, MockSystem(), config, _SilentLogger())

    assert network.events[:2] == [("country", "AU"), ("connect", config.wifi_ssid)]


def test_connect_wifi_skips_country_when_not_configured():
    config = _loaded_config()
    config.wifi_country = ""
    network = MockNetwork()

    connect_wifi(network, MockSystem(), config, _SilentLogger())

    assert network.country is None


def test_connect_wifi_sets_hostname_from_device_id():
    config = _loaded_config()
    network = MockNetwork()

    connect_wifi(network, MockSystem(), config, _SilentLogger())

    assert network.hostname == config.device_id


def test_build_device_config_defaults_wifi_country_to_au():
    template = dict(TEMPLATE, wifi_country="replace-with-wifi-country")

    config = build_device_config(template, "dev-1", API_URL, "k", "s", "p")

    assert config["wifi_country"] == "AU"


def test_build_device_config_uses_provisioned_wifi_country():
    template = dict(TEMPLATE, wifi_country="replace-with-wifi-country")

    config = build_device_config(template, "dev-1", API_URL, "k", "s", "p", wifi_country="nz")

    assert config["wifi_country"] == "NZ"


def test_write_config_passes_provisioned_wifi_country():
    fs = MockFileSystem()

    write_config(fs, _provision(wifi_country="GB"), TEMPLATE)

    assert json.loads(fs.read_text("config.json"))["wifi_country"] == "GB"
