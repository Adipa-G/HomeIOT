# Copilot Instructions — HomeIOT

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

## Python Conventions (edge/)

- MicroPython-compatible code — no CPython-only features.
- Tests use pytest and run from workspace root: `python -m pytest edge`.
