using HomeIOT.Api.Contracts;

namespace HomeIOT.Api.Services;

public interface IUserService
{
    Task<List<UserListItem>> ListUsersAsync(CancellationToken ct = default);
    Task<UserListItem?> CreateUserAsync(string username, string password, CancellationToken ct = default);
    Task<bool> ChangePasswordAsync(string username, string newPassword, CancellationToken ct = default);
    Task<bool> DeleteUserAsync(string username, CancellationToken ct = default);
}
