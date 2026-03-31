using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace api.Migrations
{
    /// <inheritdoc />
    public partial class AddModuleTables : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "module_definitions",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    ModuleId = table.Column<string>(type: "TEXT", maxLength: 128, nullable: false),
                    Description = table.Column<string>(type: "TEXT", maxLength: 1024, nullable: true),
                    DefaultEntrypoint = table.Column<string>(type: "TEXT", maxLength: 128, nullable: false, defaultValue: "run"),
                    CreatedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false),
                    UpdatedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_module_definitions", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "module_results",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    DeviceId = table.Column<string>(type: "TEXT", maxLength: 128, nullable: false),
                    ModuleId = table.Column<string>(type: "TEXT", maxLength: 128, nullable: false),
                    ModuleVersion = table.Column<string>(type: "TEXT", maxLength: 64, nullable: false),
                    RunId = table.Column<string>(type: "TEXT", maxLength: 256, nullable: false),
                    StartedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false),
                    FinishedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false),
                    ElapsedMs = table.Column<int>(type: "INTEGER", nullable: false),
                    Status = table.Column<string>(type: "TEXT", maxLength: 32, nullable: false),
                    Output = table.Column<string>(type: "TEXT", nullable: true),
                    ErrorMessage = table.Column<string>(type: "TEXT", nullable: true),
                    ReceivedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_module_results", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "module_statuses",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    DeviceId = table.Column<string>(type: "TEXT", maxLength: 128, nullable: false),
                    ModuleId = table.Column<string>(type: "TEXT", maxLength: 128, nullable: false),
                    ModuleVersion = table.Column<string>(type: "TEXT", maxLength: 64, nullable: false),
                    Disabled = table.Column<bool>(type: "INTEGER", nullable: false),
                    DisabledReason = table.Column<string>(type: "TEXT", maxLength: 512, nullable: true),
                    FailedStartCount = table.Column<int>(type: "INTEGER", nullable: false),
                    DisabledAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: true),
                    ReceivedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_module_statuses", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "module_versions",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    ModuleDefinitionId = table.Column<Guid>(type: "TEXT", nullable: false),
                    Version = table.Column<string>(type: "TEXT", maxLength: 64, nullable: false),
                    PackageHash = table.Column<string>(type: "TEXT", maxLength: 128, nullable: false),
                    PackageSizeBytes = table.Column<long>(type: "INTEGER", nullable: false),
                    CreatedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_module_versions", x => x.Id);
                    table.ForeignKey(
                        name: "FK_module_versions_module_definitions_ModuleDefinitionId",
                        column: x => x.ModuleDefinitionId,
                        principalTable: "module_definitions",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "module_assignments",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    DeviceRecordId = table.Column<Guid>(type: "TEXT", nullable: false),
                    ModuleDefinitionId = table.Column<Guid>(type: "TEXT", nullable: false),
                    ModuleVersionId = table.Column<Guid>(type: "TEXT", nullable: false),
                    IntervalMs = table.Column<int>(type: "INTEGER", nullable: false),
                    TimeoutMs = table.Column<int>(type: "INTEGER", nullable: false),
                    Entrypoint = table.Column<string>(type: "TEXT", maxLength: 128, nullable: false, defaultValue: "run"),
                    Enabled = table.Column<bool>(type: "INTEGER", nullable: false),
                    CreatedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false),
                    UpdatedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_module_assignments", x => x.Id);
                    table.ForeignKey(
                        name: "FK_module_assignments_devices_DeviceRecordId",
                        column: x => x.DeviceRecordId,
                        principalTable: "devices",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_module_assignments_module_definitions_ModuleDefinitionId",
                        column: x => x.ModuleDefinitionId,
                        principalTable: "module_definitions",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_module_assignments_module_versions_ModuleVersionId",
                        column: x => x.ModuleVersionId,
                        principalTable: "module_versions",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_module_assignments_DeviceRecordId_ModuleDefinitionId",
                table: "module_assignments",
                columns: new[] { "DeviceRecordId", "ModuleDefinitionId" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_module_assignments_ModuleDefinitionId",
                table: "module_assignments",
                column: "ModuleDefinitionId");

            migrationBuilder.CreateIndex(
                name: "IX_module_assignments_ModuleVersionId",
                table: "module_assignments",
                column: "ModuleVersionId");

            migrationBuilder.CreateIndex(
                name: "IX_module_definitions_ModuleId",
                table: "module_definitions",
                column: "ModuleId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_module_results_DeviceId_ModuleId",
                table: "module_results",
                columns: new[] { "DeviceId", "ModuleId" });

            migrationBuilder.CreateIndex(
                name: "IX_module_statuses_DeviceId_ModuleId",
                table: "module_statuses",
                columns: new[] { "DeviceId", "ModuleId" });

            migrationBuilder.CreateIndex(
                name: "IX_module_versions_ModuleDefinitionId_Version",
                table: "module_versions",
                columns: new[] { "ModuleDefinitionId", "Version" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "module_assignments");

            migrationBuilder.DropTable(
                name: "module_results");

            migrationBuilder.DropTable(
                name: "module_statuses");

            migrationBuilder.DropTable(
                name: "module_versions");

            migrationBuilder.DropTable(
                name: "module_definitions");
        }
    }
}
