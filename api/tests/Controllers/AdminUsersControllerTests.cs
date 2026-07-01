using HomeIOT.Api.Controllers;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class AdminUsersControllerTests
{
    private readonly Mock<IUserService> _mockService;
    private readonly AdminUsersController _controller;

    public AdminUsersControllerTests()
    {
        _mockService = new Mock<IUserService>();
        _controller = new AdminUsersController(_mockService.Object)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext(),
            },
        };
    }

    [Fact]
    public async Task ListUsers_ReturnsOk()
    {
        _mockService.Setup(s => s.ListUsersAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(new List<UserListItem>());

        var result = await _controller.ListUsers(CancellationToken.None);

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public async Task CreateUser_Returns201_WhenValid()
    {
        var user = new UserListItem(1, "newuser", "2026-01-01T00:00:00Z");
        _mockService.Setup(s => s.CreateUserAsync("newuser", "password123", It.IsAny<CancellationToken>()))
            .ReturnsAsync(user);

        var result = await _controller.CreateUser(
            new CreateUserRequest { Username = "newuser", Password = "password123" },
            CancellationToken.None);

        Assert.IsType<CreatedResult>(result);
    }

    [Fact]
    public async Task CreateUser_ReturnsBadRequest_WhenMissingFields()
    {
        var result = await _controller.CreateUser(
            new CreateUserRequest { Username = null, Password = null },
            CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task CreateUser_ReturnsBadRequest_WhenPasswordTooShort()
    {
        var result = await _controller.CreateUser(
            new CreateUserRequest { Username = "user", Password = "short" },
            CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task CreateUser_ReturnsConflict_WhenDuplicate()
    {
        _mockService.Setup(s => s.CreateUserAsync("existing", "password123", It.IsAny<CancellationToken>()))
            .ReturnsAsync((UserListItem?)null);

        var result = await _controller.CreateUser(
            new CreateUserRequest { Username = "existing", Password = "password123" },
            CancellationToken.None);

        Assert.IsType<ConflictObjectResult>(result);
    }

    [Fact]
    public async Task ChangePassword_ReturnsOk_WhenValid()
    {
        _mockService.Setup(s => s.ChangePasswordAsync("user", "newpass123", It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);

        var result = await _controller.ChangePassword(
            "user", new ChangePasswordRequest { NewPassword = "newpass123" }, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<StatusResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
    }

    [Fact]
    public async Task ChangePassword_ReturnsBadRequest_WhenMissing()
    {
        var result = await _controller.ChangePassword(
            "user", new ChangePasswordRequest { NewPassword = null }, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task ChangePassword_ReturnsBadRequest_WhenTooShort()
    {
        var result = await _controller.ChangePassword(
            "user", new ChangePasswordRequest { NewPassword = "short" }, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task ChangePassword_ReturnsNotFound_WhenMissing()
    {
        _mockService.Setup(s => s.ChangePasswordAsync("nonexistent", "newpass123", It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);

        var result = await _controller.ChangePassword(
            "nonexistent", new ChangePasswordRequest { NewPassword = "newpass123" }, CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task DeleteUser_ReturnsOk_WhenDeleted()
    {
        _mockService.Setup(s => s.DeleteUserAsync("user", It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);

        var result = await _controller.DeleteUser("user", CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<StatusResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
    }

    [Fact]
    public async Task DeleteUser_ReturnsNotFound_WhenMissing()
    {
        _mockService.Setup(s => s.DeleteUserAsync("nonexistent", It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);

        var result = await _controller.DeleteUser("nonexistent", CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result);
    }
}
