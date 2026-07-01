using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Infrastructure;
using Microsoft.EntityFrameworkCore;

namespace HomeIOT.Api.Services;

public sealed class UserService : IUserService
{
    private readonly ApiDbContext _db;

    public UserService(ApiDbContext db)
    {
        _db = db;
    }

    public async Task<List<UserListItem>> ListUsersAsync(CancellationToken ct = default)
    {
        return await _db.Users
            .AsNoTracking()
            .OrderBy(u => u.Username)
            .Select(u => new UserListItem(
                u.Id,
                u.Username,
                EndpointValidation.ToUtcZ(u.CreatedAtUtc)))
            .ToListAsync(ct);
    }

    public async Task<UserListItem?> CreateUserAsync(string username, string password, CancellationToken ct = default)
    {
        var exists = await _db.Users.AnyAsync(u => u.Username == username.ToLower(), ct);
        if (exists)
            return null;

        var user = new UserRecord
        {
            Username = username.ToLower(),
            PasswordHash = BCrypt.Net.BCrypt.HashPassword(password),
            CreatedAtUtc = DateTimeOffset.UtcNow
        };

        _db.Users.Add(user);
        await _db.SaveChangesAsync(ct);

        return new UserListItem(user.Id, user.Username, EndpointValidation.ToUtcZ(user.CreatedAtUtc));
    }

    public async Task<bool> ChangePasswordAsync(string username, string newPassword, CancellationToken ct = default)
    {
        var user = await _db.Users.FirstOrDefaultAsync(u => u.Username == username.ToLower(), ct);
        if (user is null)
            return false;

        user.PasswordHash = BCrypt.Net.BCrypt.HashPassword(newPassword);
        await _db.SaveChangesAsync(ct);
        return true;
    }

    public async Task<bool> DeleteUserAsync(string username, CancellationToken ct = default)
    {
        var user = await _db.Users.FirstOrDefaultAsync(u => u.Username == username.ToLower(), ct);
        if (user is null)
            return false;

        _db.Users.Remove(user);
        await _db.SaveChangesAsync(ct);
        return true;
    }
}
