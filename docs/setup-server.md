# Server Setup Guide

This guide covers installing and configuring the HomeIOT API server on your machine. Choose between direct .NET execution (for development) or Docker Compose (for containerized deployment).

## Prerequisites

- **.NET 8 SDK** — [Download](https://dotnet.microsoft.com/en-us/download/dotnet/8.0)
- **Git** — For cloning the repository
- **Docker** (optional) — Only needed for Docker Compose setup

---

## Option 1: Direct .NET Execution (Development)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd HomeIOT
```

### Step 2: Verify .NET Installation

```bash
dotnet --version
# Should output: 8.x.xxx or higher
```

### Step 3: Run the API Server

```bash
dotnet run --project api/src/api.csproj
```

**Expected output:**
```
info: Microsoft.Hosting.Lifetime[14]
      Now listening on: http://0.0.0.0:5228
```

The server is now running and listening on port **5228**.

### Step 4: Access the Web UI

Open your browser and navigate to:
```
http://localhost:5228
```

Or if connecting from another machine, use the IP address:
```
http://<your-machine-ip>:5228
```

### Step 5: Initial Login

- **Username**: `Admin`
- **Password**: `123`

⚠️ **IMPORTANT**: Change this password immediately after first login. Navigate to **Admin → Users**, select the Admin user, and change the password.

### Step 6: Database

The SQLite database is automatically created at `data/homeiot.db` on first run. This file persists between server restarts.

---

## Option 2: Docker Compose Deployment (Containerized)

For easier deployment and isolation, use Docker Compose.

### Step 1: Verify Docker Installation

```bash
docker --version
docker-compose --version
```

Both should output version information. If not installed, [download Docker Desktop](https://www.docker.com/products/docker-desktop/).

### Step 2: Create a copy of `docker-compose.yml`

Create a copy of `docker-compose.yml` file on the server and customise it. For example if you want to manage the paths of the data, 
you can use file locations instead of docker managed locations.

### Step 3: Start the Container

```bash
# Start services in background
docker-compose up -d

# View logs
docker-compose logs -f api
```

Expected output:
```
api  | info: Microsoft.Hosting.Lifetime[14]
api  |      Now listening on: http://0.0.0.0:5228
```

### Step 4: Access the Server

Open your browser and navigate to:
```
http://localhost:5228
```

Login with:
- **Username**: `Admin`
- **Password**: `123`

### Step 5: Manage Container

```bash
# Stop services
docker-compose down

# View container status
docker-compose ps

# View logs
docker-compose logs -f

# Restart services
docker-compose restart
```
---

## Hostname Assignment

### On Windows (Direct .NET)

To access the server using a custom hostname instead of localhost:

1. **Edit Windows HOSTS file**
   - Open `C:\Windows\System32\drivers\etc\hosts` as Administrator
   - Add a line:
     ```
     127.0.0.1    homeiot.local
     ```
   - Save the file

2. **Access the server**
   ```
   http://homeiot.local:5228
   ```

3. **From another machine on network**
   - Edit HOSTS file on that machine and replace `127.0.0.1` with your server's IP:
     ```
     192.168.1.100    homeiot.local
     ```
   - Access:
     ```
     http://homeiot.local:5228
     ```

### On Docker Compose

Docker Compose creates an internal network, so hostname resolution is handled automatically:

1. **Configure in docker-compose.yml** (already included above)
   ```yaml
   services:
     api:
       container_name: homeiot
       networks:
         - homeiot-network
   ```

2. **External access** — On Windows HOSTS file:
   ```
   127.0.0.1    homeiot.local
   ```
   Then access:
   ```
   http://homeiot.local:5228
   ```

3. **Between containers** — Other containers can reference by service name:
   ```
   http://api:5228
   ```

---

## Configuration

### appsettings.json

Key configuration options in `api/src/appsettings.json`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `ConnectionStrings.DefaultConnection` | `Data Source=../data/homeiot.db` | SQLite database path |
| `RuntimeControl.NextHeartbeatMs` | `60000` | Device heartbeat interval (milliseconds) |
| `RuntimeControl.DevPollIntervalMs` | `2000` | Dev command polling interval |
| `RuntimeControl.ModuleAssignmentPollIntervalMs` | `60000` | Module assignment polling interval |
| `Admin.MasterUsername` | `Admin` | Default admin username |
| `Admin.MasterPassword` | `123` | Default admin password |
| `Jwt.SecretKey` | (configured) | JWT signing key (change in production!) |
| `Jwt.ExpirationHours` | `24` | Token expiration time |

### Environment Variables (Docker)

When running in Docker, these environment variables override `appsettings.json`:

```bash
ASPNETCORE_ENVIRONMENT=Development
ASPNETCORE_URLS=http://0.0.0.0:5228
ADMIN__MASTERPASSWORD=your_secure_password
```

### Production Considerations

Before deploying to production:

1. **Change default credentials**
   ```json
   "Admin": {
     "MasterPassword": "YOUR_VERY_SECURE_PASSWORD_HERE"
   }
   ```

2. **Update JWT secret** — Generate a strong random key:
   ```powershell
   # PowerShell
   [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
   ```

3. **Update connection string** — Use a production database:
   ```json
   "ConnectionStrings": {
     "DefaultConnection": "Server=db.example.com;Database=homeiot;User=dbuser;Password=dbpass;"
   }
   ```

4. **Update CORS origins** — Remove localhost entries in `appsettings.json`

5. **Enable HTTPS** — Update `appsettings.json`:
   ```json
   "Kestrel": {
     "Endpoints": {
       "HttpsInlineAndHttp": {
         "Url": "https://0.0.0.0:5228"
       }
     }
   }
   ```

---

## Troubleshooting

### Port Already in Use

If port 5228 is already in use:

**Direct .NET:**
```bash
# Run on a different port
dotnet run --project api/src/api.csproj -- --urls=http://0.0.0.0:5229
```

**Docker Compose:**
Edit `docker-compose.yml`:
```yaml
ports:
  - "5229:5228"  # Change host port from 5228 to 5229
```

### Database Not Found

The `data/` directory is auto-created on first run. If you see connection errors:

```bash
# Ensure directory exists
mkdir data

# Run server again
dotnet run --project api/src/api.csproj
```

### Cannot Connect from Another Machine

1. **Verify server is running** on the machine with `netstat -an | findstr 5228` (Windows)
2. **Check firewall** — Allow port 5228 inbound traffic
3. **Use correct IP** — Replace `localhost` with actual machine IP
4. **Test connectivity**:
   ```bash
   ping <server-ip>
   ```

### Docker Build Fails

```bash
# Clean Docker cache and rebuild
docker-compose down
docker system prune -a
docker-compose build --no-cache
docker-compose up -d
```

---

## Next Steps

1. ✅ Server is running
2. ⏭️ [Set up an edge device](setup-edge-device.md)
3. ⏭️ [Explore the Dashboard](features-dashboard.md)
