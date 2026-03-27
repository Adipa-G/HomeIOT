using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using HomeIOT.Api.Configuration;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Route("api/admin/auth")]
public sealed class AdminAuthController : ControllerBase
{
    private readonly ApiDbContext _db;
    private readonly JwtOptions _jwtOptions;

    public AdminAuthController(ApiDbContext db, IOptions<JwtOptions> jwtOptions)
    {
        _db = db;
        _jwtOptions = jwtOptions.Value;
    }

    [HttpPost("token")]
    public async Task<ActionResult<AdminLoginResponse>> Login([FromBody] AdminLoginRequest? request)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        if (string.IsNullOrWhiteSpace(request.Username) || string.IsNullOrWhiteSpace(request.Password))
            return BadRequest(new ErrorResponse("invalid_request", "username and password are required."));

        var user = await _db.Users.FirstOrDefaultAsync(
            u => u.Username == request.Username, HttpContext.RequestAborted);

        if (user is null || !BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
            return Unauthorized(new ErrorResponse("unauthorized", "Invalid username or password."));

        var expiresAt = DateTimeOffset.UtcNow.AddHours(_jwtOptions.ExpirationHours);

        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_jwtOptions.SecretKey));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var claims = new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, user.Username),
            new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
        };

        var token = new JwtSecurityToken(
            issuer: _jwtOptions.Issuer,
            claims: claims,
            expires: expiresAt.UtcDateTime,
            signingCredentials: creds);

        var tokenString = new JwtSecurityTokenHandler().WriteToken(token);

        return Ok(new AdminLoginResponse(tokenString, expiresAt));
    }
}
