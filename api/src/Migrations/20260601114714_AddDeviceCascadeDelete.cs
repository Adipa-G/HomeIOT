using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace HomeIOT.Api.Migrations
{
    /// <inheritdoc />
    public partial class AddDeviceCascadeDelete : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddUniqueConstraint(
                name: "AK_devices_DeviceId",
                table: "devices",
                column: "DeviceId");

            migrationBuilder.AddForeignKey(
                name: "FK_module_results_devices_DeviceId",
                table: "module_results",
                column: "DeviceId",
                principalTable: "devices",
                principalColumn: "DeviceId",
                onDelete: ReferentialAction.Cascade);

            migrationBuilder.AddForeignKey(
                name: "FK_module_statuses_devices_DeviceId",
                table: "module_statuses",
                column: "DeviceId",
                principalTable: "devices",
                principalColumn: "DeviceId",
                onDelete: ReferentialAction.Cascade);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_module_results_devices_DeviceId",
                table: "module_results");

            migrationBuilder.DropForeignKey(
                name: "FK_module_statuses_devices_DeviceId",
                table: "module_statuses");

            migrationBuilder.DropUniqueConstraint(
                name: "AK_devices_DeviceId",
                table: "devices");
        }
    }
}
