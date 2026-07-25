using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace HomeIOT.Api.Migrations
{
    /// <inheritdoc />
    public partial class AddShowInDashboardToModuleAssignment : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<bool>(
                name: "ShowInDashboard",
                table: "module_assignments",
                type: "INTEGER",
                nullable: false,
                defaultValue: false);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "ShowInDashboard",
                table: "module_assignments");
        }
    }
}
