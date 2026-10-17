# HomeIOT 🏠

A comprehensive IoT platform for managing embedded devices (ESP32/Pico). This platform supports creating modules in the serverside, assigning to devices so that these can be executed on the edge devices so that result is visible on the server.


## Key Features

- **Device Management**: Add devices from the web UI with one downloaded `main.py`, then monitor and control them across platforms (ESP32, Raspberry Pi Pico)
- **Module System**: Deploy and manage versioned Python modules on devices with remote execution and result tracking
- **Interactive Dev Commands**: Execute arbitrary Python code on devices for debugging and testing
- **Dashboard Analytics**: Real-time metrics on device health, module activity, and system status. The dashboard supports visual elements such as graphs and guages.
- **OTA Updates**: Over-the-air firmware updates with rollback support
- **Comprehensive Logging**: Device logs, module results, and execution tracking for troubleshooting

## Quick Start

### 

### Running the Server (30 seconds)

**Option 1: Direct .NET Execution** (for development)
```bash
# Clone and navigate to project
git clone <repo-url>
cd HomeIOT

# Run the API server
dotnet run --project api/src/api.csproj
```

Server starts at: `http://localhost:5228`

**Option 2: Docker Compose** (for easy setup)
```bash
docker-compose up -d
```

Server accessible at: `http://localhost:5228` (or your configured hostname)

### Initial Login

1. Open `http://localhost:5228` in your browser
2. Login with credentials:
   - **Username**: `Admin`
   - **Password**: `123`
3. ⚠️ **IMPORTANT**: Change the admin password immediately in the Web UI (Users section)
4. Verify setup: Dashboard should display "0 devices online"

---

## Project Structure

```
HomeIOT/
├── api/                    # .NET 10 Backend API
│   ├── src/               # API source code (controllers, services, data)
│   └── tests/             # xUnit tests
├── edge/                  # MicroPython edge runtime
│   ├── platforms/         # Platform-specific code (ESP32, Pico)
│   ├── shared/            # Common app logic and HAL
│   ├── bootstrap/         # First-boot installer embedded in the generated main.py
│   └── tools/             # Firmware release build and dev command scripts
├── web-ui/                # React + TypeScript Web Dashboard
├── data/                  # SQLite database (auto-created)
└── docs/                  # Detailed guides and references
```

## System Architecture

```mermaid
graph TB
    subgraph "Cloud/Server"
        API["API Server<br/>(C# .NET 10)"]
        DB["Database<br/>(SQLite)"]
        WEB["Web UI<br/>(React)"]
    end
    
    subgraph "Edge Devices"
        ESP32["ESP32<br/>(MicroPython)"]
        PICO["Pico<br/>(MicroPython)"]
    end
    
    subgraph "Admin Tools"
        TOOLS["Python Tools<br/>(build release)"]
    end
    
    WEB -->|Admin API| API
    API -->|Store/Query| DB
    ESP32 -->|Device API + OTA| API
    PICO -->|Device API + OTA| API
    TOOLS -->|Release| API
    
    style API fill:#0078d4
    style WEB fill:#61dafb
    style DB fill:#00a86b
    style ESP32 fill:#ff6b35
    style PICO fill:#004e89
```

### Layers Overview

| Layer | Technology | Role |
|-------|-----------|------|
| **Web UI** | React + TypeScript + Vite | Admin dashboard for managing devices, modules, users, and monitoring |
| **API** | C# .NET 10 + Entity Framework Core | REST API for device communication and admin operations |
| **Edge Runtime** | MicroPython | Firmware running on ESP32/Pico; polls for modules, executes commands |
| **Database** | SQLite | Stores devices, modules, logs, heartbeats, users, and execution results |

---

## Getting Started Guides

### For Setup & Deployment

| Guide | Purpose |
|-------|---------|
| [📖 Server Setup](docs/setup-server.md) | Install and configure the API server (direct .NET & Docker) |
| [📖 Edge Device Setup](docs/setup-edge-device.md) | Add ESP32/Pico devices and install firmware with the generated `main.py` |

### For Feature Usage

| Guide | Purpose |
|-------|---------|
| [📖 Dashboard](docs/features-dashboard.md) | Understand real-time metrics and system status |
| [📖 Device Management](docs/features-devices.md) | Add, re-provision, monitor, filter, and control devices |
| [📖 Module System](docs/features-modules.md) | Create, upload, assign, and execute modules |
| [📖 Data Visualizations](docs/features-visualizations.md) | Configure and use gauges, charts, and threshold colors |
| [📖 User Management](docs/features-users.md) | Manage admin users and authentication |
| [📖 Dev Commands](docs/features-dev-commands.md) | Execute remote code for debugging |

---

## Prerequisites

- **C# / .NET 10 SDK** — Required to run the API server
- **Python 3.8+** — Required for edge tools (building firmware releases) and tests
- **Node.js 18+** — Required for Web UI development
- **Docker** (optional) — For containerized deployment via Docker Compose
- **mpremote** — To copy the generated `main.py` onto a device (`pip install mpremote`), or use Thonny

## Installation

### Dependencies Setup

```bash
# Clone the repository
git clone <repo-url>
cd HomeIOT

# Setup Python environment for edge tools
python -m venv .venv
.venv\Scripts\activate              # Windows
# or: source .venv/bin/activate     # macOS/Linux

pip install -r edge/requirements.txt

# Setup Node dependencies for Web UI (optional for dev)
cd web-ui
npm install
cd ..
```

### First Run

1. Start the API server (see Quick Start above)
2. Web UI opens automatically or navigate to `http://localhost:5228`
3. Login with `Admin` / `123`
4. **IMPORTANT**: Change admin password immediately

---

## Testing

All code changes require corresponding tests. Run the full test suite:

```bash
# API tests (.NET)
dotnet test api/tests/homeiot.api.tests.csproj

# Edge tests (Python)
python -m pytest edge

# Web UI tests (optional)
cd web-ui && npm test
```

---

## Development Workflow

### Typical Development Day

1. **Start API server** (background)
   ```bash
   dotnet run --project api/src/api.csproj
   ```

2. **Start Web UI dev server** (in new terminal)
   ```bash
   cd web-ui && npm run dev
   ```

3. **Access Web UI** at `http://localhost:5173` (Vite dev server)

4. **Make changes** to code and tests

5. **Run tests** to verify changes
   ```bash
   # Terminal 1: dotnet test api/tests/homeiot.api.tests.csproj
   # Terminal 2: python -m pytest edge
   # Terminal 3: npm test (in web-ui)
   ```

### Seeded Simulator Data

To load the demo device, module, variables, and visualizations, set `DevelopmentSeed:Enabled` to `true` in `api/src/appsettings.Development.json` before starting the API. The seed runs at API startup in the Development environment and only creates missing records.

The root `simulator-config.json` is configured for the seeded device (`simulator-device-1`). After starting the API, run the simulator from the repository root:

```bash
python -m edge.simulator.worker --config simulator-config.json
```

The `demo-sensor` readings cycle through the configured threshold bands, including the default color below the first threshold. Let the simulator run for a few cycles to see the visualization colors and build chart history. The seed does not generate the simulator config; see [Server Setup](docs/setup-server.md) for the seed credentials and setup details.

### Code Conventions

- **C# / API**: One class per file, `PascalCase` file names, records for DTOs, `snake_case` JSON properties
- **Python / Edge**: MicroPython-compatible, pytest tests in `edge/shared/tests/`
- **TypeScript / Web**: React components in `src/components/`, pages in `src/pages/`

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for detailed conventions.

---

## Typical Workflows

### Setting Up a New Device

1. **Publish a firmware release** for the platform (once per version)
   ```bash
   python edge/tools/build_artifact.py --platform esp32 --version 1.0.0
   ```
   When the API runs elsewhere (e.g. Docker), upload the release zip on the **OTA** page instead.

2. **Add the device** under **Devices > Add device**. Enter the device ID, platform, API URL (an IP or a hostname the device can resolve) and WiFi credentials. The browser downloads `main.py`.

3. **Install on the board.** Flash MicroPython, then copy the file and reset:
   ```bash
   mpremote cp main.py :main.py
   mpremote reset
   ```
   The installer writes `config.json`, connects to WiFi, and installs the latest release through OTA. Delete the downloaded `main.py` afterwards, because it contains the device key and WiFi password.

4. **Verify in Dashboard** — Device should appear online within 60 seconds

👉 Full guide: [Edge Device Setup](docs/setup-edge-device.md)

### Creating and Assigning a Module

1. Navigate to **Admin → Modules → Create Module**
2. Upload Python file with `exec()`-compatible code
3. Navigate to module detail → **Assign**
4. Select target devices and version
5. Device fetches and executes within 60 seconds
6. View results in device detail → **Module Results**

👉 Full guide: [Module System](docs/features-modules.md)

### Debugging a Device with Dev Commands

1. Navigate to **Admin → Dev Commands**
2. Write Python code (e.g., `print(device_info)`)
3. Select target device
4. Queue command
5. View result in real-time (device executes within 2 seconds)

👉 Full guide: [Dev Commands](docs/features-dev-commands.md)

---

## Configuration & Customization

### Server Configuration

Edit `api/src/appsettings.json`:

```json
{
  "RuntimeControl": {
    "NextHeartbeatMs": 60000,                    // Device heartbeat interval
    "DevPollIntervalMs": 2000,                   // Dev command polling
    "ModuleAssignmentPollIntervalMs": 60000      // Module assignment polling
  },
  "Admin": {
    "MasterUsername": "Admin",
    "MasterPassword": "YOUR_SECURE_PASSWORD"    // Change in production!
  }
}
```

For production, also change:
- `Jwt.SecretKey` — Use a cryptographically secure random key
- `ConnectionStrings.DefaultConnection` — Use production database
- Remove CORS localhost origins in `appsettings.json`

### Device Configuration

Device `config.json` is written on the device by the `main.py` installer from **Add device** / **Re-provision**, and includes:
- WiFi credentials and API key (encrypted, device-ID-bound)
- API URL and authentication
- Polling intervals and power settings
- Logging configuration

---

## Troubleshooting

### Device not appearing in dashboard
- Check API URL is correct and reachable from device (bare machine names like `homesvr` often don't resolve on the device; use an IP)
- Watch the `[bootstrap]` output with `mpremote repl` during first install
- Verify WiFi connection on device (use dev commands to test)
- Check device logs via `GET /api/devices/{id}/logs` in dashboard

### Module not executing
- Verify module syntax is correct (test locally first with dev commands)
- Check device is online (heartbeat recent)
- View module result for error details

### Web UI not loading
- Confirm API server is running on port 5228
- Check CORS configuration in `appsettings.json` includes your origin
- Clear browser cache and reload

For more, see the detailed guides linked above.

---

## License

GNU AFFERO GENERAL PUBLIC LICENSE Version 3

## Support

For issues, questions, or feature requests, please open an issue in the repository.
