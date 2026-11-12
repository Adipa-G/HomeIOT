# Copilot Instructions — HomeIOT

## Testing Requirements

- **Every code change must include corresponding tests.** When adding or modifying a feature, add or update tests in the same commit.
- **API (.NET):** Add xUnit tests in `api/tests/`. One test class per production class. Run with `dotnet test api/tests/homeiot.api.tests.csproj`.
- **Edge (Python):** Add pytest tests in `edge/shared/tests/`. Run with `uv run --project edge pytest edge`.
- **Web UI (React):** Add Vitest tests in `web-ui/src/test/`. Run with `cd web-ui && npx vitest run`.
- **Verify all three suites pass** after any change that touches multiple layers.

## .NET / C# Conventions (api/)

- **One type per file.** Each class, record, struct, enum, or interface gets its own `.cs` file named after the type. Private nested types within a class are fine.
- **File naming:** File name must match the type name exactly (e.g., `DeviceRecord.cs` for `public sealed class DeviceRecord`).
- **Namespace per folder:** Use folder-based namespaces matching the directory structure (e.g., `HomeIOT.Api.Contracts`, `HomeIOT.Api.Data.Entities`).
- **Records for immutable DTOs:** Use `record` for response contracts and value objects. Use `class` for request DTOs that need mutable properties with `[JsonPropertyName]`.
- **snake_case JSON:** All JSON property names use `snake_case` via `[JsonPropertyName("...")]` attributes.
- **UTC timestamps:** Format as ISO 8601 with Z suffix using `EndpointValidation.ToUtcZ()`.
- **Controller base classes:** Device-facing endpoints inherit `EdgeApiControllerBase`. Admin endpoints inherit `UserApiControllerBase` with `[Authorize]`.
- **Service pattern:** Define `IService` interface and `Service` implementation in separate files under `Services/`. Service-related DTOs/models (e.g., `OtaFileContent`, `DevCommandEntry`) go in `Services/Models/` with namespace `HomeIOT.Api.Services.Models`.
- **Entity pattern:** EF Core entities go in `Data/Entities/` with `Record` suffix (e.g., `DeviceRecord`).
- **Test pattern:** Use xUnit with Moq. One test class per production class. Use `InMemoryDatabase` for DB tests, `Mock<T>` for service dependencies in controller tests.
- **No anonymous types in responses:** Never return `new { ... }` from a controller action. Always define a named `sealed record` in `api/src/Contracts/` and return that instead. Use the existing `StatusResponse` for simple `{ status: "ok" }` responses.

## Python Conventions (edge/)

- MicroPython-compatible code — no CPython-only features.
- Python dependencies live in `edge/pyproject.toml` and `edge/uv.lock`, with the environment in `edge/.venv`. From the workspace root, set up with `uv sync --project edge`; add packages with `uv add --project edge` (or `uv add --project edge --dev` for tooling), never by hand-editing a requirements file.
- Tests use pytest and run from workspace root: `uv run --project edge pytest edge`.
- Code must pass `pyright` (standard mode, config in `[tool.pyright]` in `edge/pyproject.toml`). Run from workspace root: `uv run --project edge pyright -p edge`.
- Folders listed in `strict` in `[tool.pyright]` (currently `bootstrap`, `platforms`, `shared/hal`, `shared/tests/mocks`, `simulator` and `tools`) are checked in strict mode: every parameter and return needs a type. Folders are added one at a time once fully typed. Use builtin generics (`dict[str, int]`, `list[str]`, `tuple[int, ...]`); the firmware has no `typing` module, and releases are compiled, so annotations cost nothing on the device. Desktop-only code (tests, simulator, tools) may import from `typing`.
- In device code, type-only imports (`typing`, `types.ModuleType`, `collections.abc`, `requests`, `machine` classes) go in a `TYPE_CHECKING = False` / `if TYPE_CHECKING:` block, and annotations that use them are strings (`"Iterable[bytes]"`). That block never runs on a device. Pass MicroPython modules around as `"ModuleType"` parameters or attributes, and call MicroPython-only functions on standard modules through `getattr(gc, "mem_free")()` rather than a `# pyright: ignore`.
- In strict test folders: type fixtures (`monkeypatch: pytest.MonkeyPatch`), give empty containers an element type (`calls: list[int] = []`), and use small typed functions instead of lambdas for recorded calls. A test that deliberately checks private state disables `reportPrivateUsage` for that file only, with a comment saying why.
- Releases ship every module precompiled to `.mpy` except `boot.py` and `main.py`. Each release starts with `mpy_probe.mpy` (`edge/shared/mpy_probe.py`); the updater and the installer import it before installing to confirm the firmware loads the release. Keep `mpy_probe.py` first in `_collect_files()` and in `bundle.json`'s `release_files`.
- Target MicroPython 1.28+ (ESP32 1.30, Pico W 1.28). Import modules by their plain names (`os`, `time`, `hashlib`, `binascii`, `requests`), never the deprecated `u`-prefixed aliases, and don't add desktop fallbacks for them.
- MicroPython APIs are typed by `micropython-esp32-stubs` (dev dependency). Pico-only modules (e.g. `rp2`) are stubbed by hand in `edge/typings/`; add declarations there as new Pico APIs come into use. MicroPython extras on standard modules (`time.ticks_ms`, `time.sleep_ms`, `gc.mem_free`, `sys.print_exception`) are checked against CPython's stdlib, so they still get a targeted `# pyright: ignore[reportAttributeAccessIssue]` comment. In tests, build fake MicroPython modules with `fake_module()` from `edge/shared/tests/mocks/fake_module.py`, and have mocks subclass the `edge/shared/hal/interfaces.py` interfaces.
