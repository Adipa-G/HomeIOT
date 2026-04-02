using HomeIOT.Api.Contracts;

namespace HomeIOT.Api.Services;

public interface IUserService
{
    Task<List<UserListItem>> ListUsersAsync(CancellationToken ct = default);
    Task<UserListItem?> CreateUserAsync(string username, string password, CancellationToken ct = default);
    Task<bool> ChangePasswordAsync(int userId, string newPassword, CancellationToken ct = default);
    Task<bool> DeleteUserAsync(int userId, CancellationToken ct = default);
}
