using HomeIOT.Api.Configuration;
using HomeIOT.Api.Controllers;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class AdminAuthControllerTests
{
    [Fact]
    public async Task Login_ValidCredentials_ReturnsToken()
    {
        await using var dbContext = CreateDbContext();
        await SeedUser(dbContext, "Admin", "123");
        var controller = CreateController(dbContext);

        var result = await controller.Login(new AdminLoginRequest("Admin", "123"));

        var okResult = Assert.IsType<OkObjectResult>(result.Result);
        var response = Assert.IsType<AdminLoginResponse>(okResult.Value);
        Assert.False(string.IsNullOrWhiteSpace(response.Token));
        Assert.True(response.ExpiresAt > DateTimeOffset.UtcNow);
    }

    [Fact]
    public async Task Login_WrongPassword_Returns401()
    {
        await using var dbContext = CreateDbContext();
        await SeedUser(dbContext, "Admin", "123");
        var controller = CreateController(dbContext);

        var result = await controller.Login(new AdminLoginRequest("Admin", "wrong"));

        var unauthorizedResult = Assert.IsType<UnauthorizedObjectResult>(result.Result);
        var error = Assert.IsType<ErrorResponse>(unauthorizedResult.Value);
        Assert.Equal("unauthorized", error.Error);
    }

    [Fact]
    public async Task Login_UnknownUser_Returns401()
    {
        await using var dbContext = CreateDbContext();
        var controller = CreateController(dbContext);

        var result = await controller.Login(new AdminLoginRequest("nobody", "123"));

        Assert.IsType<UnauthorizedObjectResult>(result.Result);
    }

    [Fact]
    public async Task Login_NullBody_Returns400()
    {
        await using var dbContext = CreateDbContext();
        var controller = CreateController(dbContext);

        var result = await controller.Login(null);

        Assert.IsType<BadRequestObjectResult>(result.Result);
    }

    [Fact]
    public async Task Login_MissingUsername_Returns400()
    {
        await using var dbContext = CreateDbContext();
        var controller = CreateController(dbContext);

        var result = await controller.Login(new AdminLoginRequest(null, "123"));

        Assert.IsType<BadRequestObjectResult>(result.Result);
    }

    private static AdminAuthController CreateController(ApiDbContext dbContext)
    {
        var jwtOptions = Options.Create(new JwtOptions
        {
            SecretKey = "TestSecretKey-Must-Be-At-Least-32-Characters!",
            Issuer = "HomeIOT-Test",
            ExpirationHours = 24,
        });

        var controller = new AdminAuthController(dbContext, jwtOptions);
        controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext(),
        };
        return controller;
    }

    private static async Task SeedUser(ApiDbContext dbContext, string username, string password)
    {
        dbContext.Users.Add(new UserRecord
        {
            Username = username,
            PasswordHash = BCrypt.Net.BCrypt.HashPassword(password),
            CreatedAtUtc = DateTimeOffset.UtcNow,
        });
        await dbContext.SaveChangesAsync();
    }

    private static ApiDbContext CreateDbContext()
    {
        var options = new DbContextOptionsBuilder<ApiDbContext>()
            .UseSqlite("Data Source=:memory:;")
            .Options;
        var dbContext = new ApiDbContext(options);
        dbContext.Database.OpenConnection();
        dbContext.Database.EnsureCreated();
        return dbContext;
    }
}
