using HomeIOT.Api.Data;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace HomeIOT.Api.Migrations
{
    [DbContext(typeof(ApiDbContext))]
    [Migration("20260601113000_AddModuleResultVariableValues")]
    public partial class AddModuleResultVariableValues : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "VariableValues",
                table: "module_results",
                type: "TEXT",
                nullable: true);
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "VariableValues",
                table: "module_results");
        }
    }
}
