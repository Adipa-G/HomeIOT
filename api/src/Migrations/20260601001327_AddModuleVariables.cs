using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace api.Migrations
{
    /// <inheritdoc />
    public partial class AddModuleVariables : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "module_variable_defs",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    ModuleDefinitionId = table.Column<Guid>(type: "TEXT", nullable: false),
                    Name = table.Column<string>(type: "TEXT", maxLength: 64, nullable: false),
                    Type = table.Column<string>(type: "TEXT", maxLength: 16, nullable: false, defaultValue: "string"),
                    DefaultValue = table.Column<string>(type: "TEXT", maxLength: 1024, nullable: true),
                    Description = table.Column<string>(type: "TEXT", maxLength: 512, nullable: true),
                    ServerCode = table.Column<string>(type: "TEXT", nullable: true),
                    CreatedAtUtc = table.Column<string>(type: "TEXT", nullable: false),
                    UpdatedAtUtc = table.Column<string>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_module_variable_defs", x => x.Id);
                    table.ForeignKey(
                        name: "FK_module_variable_defs_module_definitions_ModuleDefinitionId",
                        column: x => x.ModuleDefinitionId,
                        principalTable: "module_definitions",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "module_variable_values",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    ModuleAssignmentId = table.Column<Guid>(type: "TEXT", nullable: false),
                    VariableName = table.Column<string>(type: "TEXT", maxLength: 64, nullable: false),
                    Value = table.Column<string>(type: "TEXT", maxLength: 1024, nullable: true),
                    ComputedByServer = table.Column<bool>(type: "INTEGER", nullable: false),
                    LastComputedAtUtc = table.Column<string>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_module_variable_values", x => x.Id);
                    table.ForeignKey(
                        name: "FK_module_variable_values_module_assignments_ModuleAssignmentId",
                        column: x => x.ModuleAssignmentId,
                        principalTable: "module_assignments",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_module_variable_defs_ModuleDefinitionId_Name",
                table: "module_variable_defs",
                columns: new[] { "ModuleDefinitionId", "Name" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_module_variable_values_ModuleAssignmentId_VariableName",
                table: "module_variable_values",
                columns: new[] { "ModuleAssignmentId", "VariableName" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "module_variable_defs");

            migrationBuilder.DropTable(
                name: "module_variable_values");
        }
    }
}
