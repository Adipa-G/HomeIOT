# Multi-stage build for HomeIOT API
# Stage 1: Build
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build

WORKDIR /src

# Copy project files
COPY ["api/src/api.csproj", "api/src/"]
COPY ["api/tests/homeiot.api.tests.csproj", "api/tests/"]

# Restore dependencies
RUN dotnet restore "api/src/api.csproj"

# Copy full source
COPY . .

# Build release
RUN dotnet build "api/src/api.csproj" -c Release -o /app/build

# Stage 2: Publish
FROM build AS publish

RUN dotnet publish "api/src/api.csproj" -c Release -o /app/publish

# Stage 3: Runtime
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime

WORKDIR /app

# Copy published application from publish stage
COPY --from=publish /app/publish .

# Create data directory for SQLite database (will be mounted as volume)
RUN mkdir -p data

# Expose port for API
EXPOSE 5228

# Set entry point
ENTRYPOINT ["dotnet", "api.dll"]
