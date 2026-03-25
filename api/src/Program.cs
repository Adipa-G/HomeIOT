using HomeIOT.Api.Configuration;
using HomeIOT.Api.Controllers;
using HomeIOT.Api.Data;
using HomeIOT.Api.Infrastructure;
using HomeIOT.Api.Services;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

builder.Services.Configure<RuntimeControlOptions>(builder.Configuration.GetSection(RuntimeControlOptions.SectionName));
builder.Services.Configure<OtaArtifactOptions>(builder.Configuration.GetSection(OtaArtifactOptions.SectionName));
builder.Services.AddDbContext<ApiDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("DefaultConnection")));
builder.Services.AddSingleton<IOtaReleaseService, FileSystemOtaReleaseService>();
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

// Initialize database
using (var scope = app.Services.CreateScope())
{
    var dbContext = scope.ServiceProvider.GetRequiredService<ApiDbContext>();
    dbContext.Database.Migrate();
}

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

// Register middleware
app.UseMiddleware<DeviceAuthMiddleware>();

// Health check endpoint
app.MapGet("/", () => Results.Ok(new { status = "ok", service = "HomeIOT API" }));

// Register MVC controller endpoints
app.MapControllers();

app.Run();
