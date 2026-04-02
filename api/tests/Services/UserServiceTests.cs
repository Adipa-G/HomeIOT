using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Services;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public class UserServiceTests : IDisposable
{
    private readonly ApiDbContext _db;
    private readonly UserService _service;

    public UserServiceTests()
    {
        var options = new DbContextOptionsBuilder<ApiDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        _db = new ApiDbContext(options);
        _service = new UserService(_db);
    }

    public void Dispose()
    {
        _db.Dispose();
    }

    [Fact]
    public async Task ListUsers_ReturnsAll()
    {
        _db.Users.Add(new UserRecord
        {
            Username = "admin",
            PasswordHash = BCrypt.Net.BCrypt.HashPassword("password"),
            CreatedAtUtc = DateTimeOffset.UtcNow,
        });
        await _db.SaveChangesAsync();

        var result = await _service.ListUsersAsync();

        Assert.Single(result);
        Assert.Equal("admin", result[0].Username);
    }

    [Fact]
    public async Task CreateUser_CreatesAndReturnsItem()
    {
        var result = await _service.CreateUserAsync("newuser", "password123");

        Assert.NotNull(result);
        Assert.Equal("newuser", result.Username);
        Assert.True(await _db.Users.AnyAsync(u => u.Username == "newuser"));
    }

    [Fact]
    public async Task CreateUser_DuplicateUsername_ReturnsNull()
    {
        _db.Users.Add(new UserRecord
        {
            Username = "existing",
            PasswordHash = BCrypt.Net.BCrypt.HashPassword("password"),
            CreatedAtUtc = DateTimeOffset.UtcNow,
        });
        await _db.SaveChangesAsync();

        var result = await _service.CreateUserAsync("existing", "password123");

        Assert.Null(result);
    }

    [Fact]
    public async Task ChangePassword_UpdatesHash()
    {
        _db.Users.Add(new UserRecord
        {
            Username = "admin",
            PasswordHash = BCrypt.Net.BCrypt.HashPassword("oldpass"),
            CreatedAtUtc = DateTimeOffset.UtcNow,
        });
        await _db.SaveChangesAsync();
        var user = await _db.Users.FirstAsync();

        var result = await _service.ChangePasswordAsync(user.Id, "newpass123");

        Assert.True(result);
        var updated = await _db.Users.FirstAsync();
        Assert.True(BCrypt.Net.BCrypt.Verify("newpass123", updated.PasswordHash));
    }

    [Fact]
    public async Task ChangePassword_NotFound_ReturnsFalse()
    {
        var result = await _service.ChangePasswordAsync(999, "newpass");
        Assert.False(result);
    }

    [Fact]
    public async Task DeleteUser_RemovesAndReturnsTrue()
    {
        _db.Users.Add(new UserRecord
        {
            Username = "todelete",
            PasswordHash = BCrypt.Net.BCrypt.HashPassword("password"),
            CreatedAtUtc = DateTimeOffset.UtcNow,
        });
        await _db.SaveChangesAsync();
        var user = await _db.Users.FirstAsync();

        var result = await _service.DeleteUserAsync(user.Id);

        Assert.True(result);
        Assert.False(await _db.Users.AnyAsync());
    }

    [Fact]
    public async Task DeleteUser_NotFound_ReturnsFalse()
    {
        var result = await _service.DeleteUserAsync(999);
        Assert.False(result);
    }
}
