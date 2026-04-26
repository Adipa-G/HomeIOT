using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/admin/users")]
public sealed class AdminUsersController : UserApiControllerBase
{
    private readonly IUserService _userService;

    public AdminUsersController(IUserService userService)
    {
        _userService = userService;
    }

    [HttpGet]
    public async Task<IActionResult> ListUsers(CancellationToken ct)
    {
        var users = await _userService.ListUsersAsync(ct);
        return Ok(users);
    }

    [HttpPost]
    public async Task<IActionResult> CreateUser(
        [FromBody] CreateUserRequest? request, CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        if (string.IsNullOrWhiteSpace(request.Username) || string.IsNullOrWhiteSpace(request.Password))
            return BadRequest(new ErrorResponse("invalid_request", "username and password are required."));

        if (request.Password.Length < 8)
            return BadRequest(new ErrorResponse("invalid_request", "password must be at least 8 characters."));

        var user = await _userService.CreateUserAsync(request.Username.Trim(), request.Password, ct);
        if (user is null)
            return Conflict(new ErrorResponse("conflict", "Username already exists."));

        return Created($"/api/admin/users/{user.Id}", user);
    }

    [HttpPut("{userId:int}/password")]
    public async Task<IActionResult> ChangePassword(
        int userId, [FromBody] ChangePasswordRequest? request, CancellationToken ct)
    {
        if (request is null || string.IsNullOrWhiteSpace(request.NewPassword))
            return BadRequest(new ErrorResponse("invalid_request", "new_password is required."));

        if (request.NewPassword.Length < 8)
            return BadRequest(new ErrorResponse("invalid_request", "new_password must be at least 8 characters."));

        var changed = await _userService.ChangePasswordAsync(userId, request.NewPassword, ct);
        if (!changed)
            return NotFound(new ErrorResponse("not_found", "User not found."));

        return Ok(new StatusResponse("ok"));
    }

    [HttpDelete("{userId:int}")]
    public async Task<IActionResult> DeleteUser(int userId, CancellationToken ct)
    {
        var deleted = await _userService.DeleteUserAsync(userId, ct);
        if (!deleted)
            return NotFound(new ErrorResponse("not_found", "User not found."));

        return Ok(new StatusResponse("ok"));
    }
}
