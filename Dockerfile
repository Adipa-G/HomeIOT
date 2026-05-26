# Multi-stage build for HomeIOT API with React frontend
# Stage 1: Build React frontend
FROM node:20-alpine AS react-build

WORKDIR /src/web-ui

# Copy React app files
COPY ["web-ui/package.json", "web-ui/package-lock.json", "./"]

# Install dependencies
RUN npm ci

# Copy source
COPY ["web-ui/", "./"]

# Build for production
RUN npm run build

# Stage 2: Build .NET API
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS api-build

WORKDIR /src

# Copy project files
COPY ["api/src/api.csproj", "api/src/"]

# Restore dependencies
RUN dotnet restore "api/src/api.csproj"

# Copy full source
COPY . .

# Build release
RUN dotnet build "api/src/api.csproj" -c Release -o /app/build

# Stage 3: Publish
FROM api-build AS publish

RUN dotnet publish "api/src/api.csproj" -c Release -o /app/publish

# Stage 4: Runtime
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime

WORKDIR /app

# Copy published application from publish stage
COPY --from=publish /app/publish .

# Copy React build artifacts to wwwroot
COPY --from=react-build /src/web-ui/dist ./wwwroot

# Create data directory for SQLite database (will be mounted as volume)
RUN mkdir -p data

# Expose port for API
EXPOSE 5228

# Set entry point
ENTRYPOINT ["dotnet", "api.dll"]
