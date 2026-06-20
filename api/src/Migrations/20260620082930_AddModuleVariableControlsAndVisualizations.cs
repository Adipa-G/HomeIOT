using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace HomeIOT.Api.Migrations
{
    /// <inheritdoc />
    public partial class AddModuleVariableControlsAndVisualizations : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "ControlType",
                table: "module_variable_defs",
                type: "TEXT",
                maxLength: 32,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "ControlOptions",
                table: "module_variable_defs",
                type: "TEXT",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "InferredJsonSchema",
                table: "module_variable_defs",
                type: "TEXT",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "module_variable_visualizations",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    ModuleVariableDefId = table.Column<Guid>(type: "TEXT", nullable: false),
                    JsonPath = table.Column<string>(type: "TEXT", maxLength: 256, nullable: false),
                    DisplayName = table.Column<string>(type: "TEXT", maxLength: 128, nullable: false),
                    VisualizationType = table.Column<string>(type: "TEXT", maxLength: 32, nullable: true),
                    VisualizationConfig = table.Column<string>(type: "TEXT", nullable: true),
                    CreatedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false),
                    UpdatedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_module_variable_visualizations", x => x.Id);
                    table.ForeignKey(
                        name: "FK_module_variable_visualizations_module_variable_defs_ModuleVariableDefId",
                        column: x => x.ModuleVariableDefId,
                        principalTable: "module_variable_defs",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_module_variable_visualizations_ModuleVariableDefId",
                table: "module_variable_visualizations",
                column: "ModuleVariableDefId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "module_variable_visualizations");

            migrationBuilder.DropColumn(
                name: "ControlType",
                table: "module_variable_defs");

            migrationBuilder.DropColumn(
                name: "ControlOptions",
                table: "module_variable_defs");

            migrationBuilder.DropColumn(
                name: "InferredJsonSchema",
                table: "module_variable_defs");
        }
    }
}
