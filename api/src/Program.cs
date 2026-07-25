using System.Reflection;
using System.Text;
using HomeIOT.Api.Configuration;
using HomeIOT.Api.Controllers;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Infrastructure;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;

var builder = WebApplication.CreateBuilder(args);

builder.Configuration.AddJsonFile("appsettings.json", optional: true, reloadOnChange: true)
                     .AddJsonFile($"appsettings.{builder.Environment.EnvironmentName}.json", optional: true, reloadOnChange: true)
                     .AddEnvironmentVariables();

builder.Services.Configure<RuntimeControlOptions>(builder.Configuration.GetSection(RuntimeControlOptions.SectionName));
builder.Services.Configure<OtaArtifactOptions>(builder.Configuration.GetSection(OtaArtifactOptions.SectionName));
builder.Services.Configure<ModuleStorageOptions>(builder.Configuration.GetSection(ModuleStorageOptions.SectionName));
builder.Services.Configure<DeviceCodeTemplateOptions>(builder.Configuration.GetSection(DeviceCodeTemplateOptions.SectionName));
builder.Services.Configure<ServerCodeTemplateOptions>(builder.Configuration.GetSection(ServerCodeTemplateOptions.SectionName));
builder.Services.Configure<JwtOptions>(builder.Configuration.GetSection(JwtOptions.SectionName));
builder.Services.Configure<AdminOptions>(builder.Configuration.GetSection(AdminOptions.SectionName));
builder.Services.Configure<DataRetentionOptions>(builder.Configuration.GetSection(DataRetentionOptions.SectionName));
builder.Services.AddDbContext<ApiDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("DefaultConnection")));
builder.Services.AddSingleton<IOtaReleaseService, FileSystemOtaReleaseService>();
builder.Services.AddSingleton<IDevCommandQueue, DevCommandQueue>();
builder.Services.AddScoped<IModuleService, ModuleService>();
builder.Services.AddScoped<IModuleVariableService, ModuleVariableService>();
builder.Services.AddScoped<IDeviceCodeTemplateService, DeviceCodeTemplateService>();
builder.Services.AddScoped<IServerCodeTemplateService, ServerCodeTemplateService>();
builder.Services.AddScoped<IModuleServerCodeService, ModuleServerCodeService>();
builder.Services.AddScoped<IDeviceAdminService, DeviceAdminService>();
builder.Services.AddScoped<IUserService, UserService>();
builder.Services.AddHostedService<DataRetentionCleanupService>();

builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        var origins = builder.Configuration.GetSection("Cors:AllowedOrigins").Get<string[]>()
            ?? new[] { "http://localhost:3000", "http://localhost:5173" };
        policy.WithOrigins(origins)
              .AllowAnyHeader()
              .AllowAnyMethod()
              .AllowCredentials();
    });
});

var jwtOptions = builder.Configuration.GetSection(JwtOptions.SectionName).Get<JwtOptions>() ?? new JwtOptions();
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidIssuer = jwtOptions.Issuer,
            ValidateAudience = false,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtOptions.SecretKey)),
        };
    });
builder.Services.AddAuthorization();

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "HomeIOT API",
        Version = "v1",
        Description = "Device management, OTA updates, dev commands, and module runtime for HomeIOT edge devices.",
    });

    // Device auth headers (used by /api/devices/* and /api/ota/* endpoints)
    options.AddSecurityDefinition("DeviceId", new OpenApiSecurityScheme
    {
        Type = SecuritySchemeType.ApiKey,
        In = ParameterLocation.Header,
        Name = "X-Device-ID",
        Description = "Device identifier (authoritative identity source).",
    });
    options.AddSecurityDefinition("ApiKey", new OpenApiSecurityScheme
    {
        Type = SecuritySchemeType.ApiKey,
        In = ParameterLocation.Header,
        Name = "X-Api-Key",
        Description = "Device API key.",
    });

    // JWT bearer (used by /api/admin/* endpoints)
    options.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Type = SecuritySchemeType.Http,
        Scheme = "bearer",
        BearerFormat = "JWT",
        Description = "JWT token obtained from POST /api/admin/auth/token.",
    });

    // Apply all schemes globally — controllers that don't need one will simply ignore it
    options.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme { Reference = new OpenApiReference { Type = ReferenceType.SecurityScheme, Id = "DeviceId" } },
            Array.Empty<string>()
        },
        {
            new OpenApiSecurityScheme { Reference = new OpenApiReference { Type = ReferenceType.SecurityScheme, Id = "ApiKey" } },
            Array.Empty<string>()
        },
        {
            new OpenApiSecurityScheme { Reference = new OpenApiReference { Type = ReferenceType.SecurityScheme, Id = "Bearer" } },
            Array.Empty<string>()
        },
    });

    // Include XML doc comments
    var xmlFile = $"{Assembly.GetExecutingAssembly().GetName().Name}.xml";
    var xmlPath = Path.Combine(AppContext.BaseDirectory, xmlFile);
    if (File.Exists(xmlPath))
        options.IncludeXmlComments(xmlPath);
});

var app = builder.Build();

// Initialize database and seed master admin
using (var scope = app.Services.CreateScope())
{
    var dbContext = scope.ServiceProvider.GetRequiredService<ApiDbContext>();
    dbContext.Database.Migrate();

    var adminOptions = builder.Configuration.GetSection(AdminOptions.SectionName).Get<AdminOptions>() ?? new AdminOptions();
    if (!string.IsNullOrWhiteSpace(adminOptions.MasterPassword))
    {
        var existing = await dbContext.Users.FirstOrDefaultAsync(u => u.Username == adminOptions.MasterUsername);
        var hash = BCrypt.Net.BCrypt.HashPassword(adminOptions.MasterPassword);
        if (existing is null)
        {
            dbContext.Users.Add(new UserRecord
            {
                Username = adminOptions.MasterUsername,
                PasswordHash = hash,
                CreatedAtUtc = DateTimeOffset.UtcNow,
            });
        }
        else
        {
            existing.PasswordHash = hash;
        }
        await dbContext.SaveChangesAsync();
    }
}

// Create module platform folders if they don't exist
var moduleOptions = builder.Configuration.GetSection(OtaArtifactOptions.SectionName).Get<OtaArtifactOptions>() ?? new OtaArtifactOptions();
var configuredModulesRoot = string.IsNullOrWhiteSpace(moduleOptions.ArtifactRoot)
    ? "../modules"
    : moduleOptions.ArtifactRoot;
var modulesPath = Path.IsPathRooted(configuredModulesRoot)
    ? Path.GetFullPath(configuredModulesRoot)
    : Path.GetFullPath(Path.Combine(app.Environment.ContentRootPath, configuredModulesRoot));
Directory.CreateDirectory(Path.Combine(modulesPath, "esp32"));
Directory.CreateDirectory(Path.Combine(modulesPath, "pico"));

app.UseSwagger();
app.UseSwaggerUI();

// Register middleware
app.UseCors();
app.UseAuthentication();
app.UseAuthorization();
app.UseMiddleware<DeviceAuthMiddleware>();

// Serve static files from wwwroot (React app)
app.UseStaticFiles();

// Register MVC controller endpoints
app.MapControllers();

// Health check endpoint (moved to /health so root serves React app)
app.MapGet("/health", () => Results.Ok(new { status = "ok", service = "HomeIOT API" }));

// Fallback route for SPA — serve index.html for unmatched routes
app.MapFallbackToFile("index.html");

app.Run();
