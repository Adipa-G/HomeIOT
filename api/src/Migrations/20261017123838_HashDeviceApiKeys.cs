using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace HomeIOT.Api.Migrations
{
    /// <inheritdoc />
    public partial class HashDeviceApiKeys : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Existing plaintext keys are kept and re-hashed by DeviceAuthMiddleware on the device's next request.
            migrationBuilder.RenameColumn(
                name: "ApiKey",
                table: "devices",
                newName: "ApiKeyHash");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.RenameColumn(
                name: "ApiKeyHash",
                table: "devices",
                newName: "ApiKey");
        }
    }
}
