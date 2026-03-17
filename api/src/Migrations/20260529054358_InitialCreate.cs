using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace api.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "devices",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    DeviceId = table.Column<string>(type: "TEXT", maxLength: 128, nullable: false),
                    ApiKey = table.Column<string>(type: "TEXT", maxLength: 512, nullable: false),
                    Platform = table.Column<string>(type: "TEXT", maxLength: 32, nullable: true),
                    Version = table.Column<string>(type: "TEXT", maxLength: 64, nullable: true),
                    Ip = table.Column<string>(type: "TEXT", maxLength: 128, nullable: true),
                    Mode = table.Column<string>(type: "TEXT", maxLength: 32, nullable: false, defaultValue: "production"),
                    CreatedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false),
                    UpdatedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false),
                    LastHeartbeatAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_devices", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "heartbeats",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    DeviceRecordId = table.Column<Guid>(type: "TEXT", nullable: false),
                    ClientTimestamp = table.Column<long>(type: "INTEGER", nullable: true),
                    UptimeMs = table.Column<long>(type: "INTEGER", nullable: true),
                    FreeMemoryBytes = table.Column<long>(type: "INTEGER", nullable: true),
                    ReceivedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_heartbeats", x => x.Id);
                    table.ForeignKey(
                        name: "FK_heartbeats_devices_DeviceRecordId",
                        column: x => x.DeviceRecordId,
                        principalTable: "devices",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "log_batches",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    DeviceRecordId = table.Column<Guid>(type: "TEXT", nullable: false),
                    Reason = table.Column<string>(type: "TEXT", maxLength: 64, nullable: false),
                    SentAt = table.Column<long>(type: "INTEGER", nullable: false),
                    DroppedCount = table.Column<int>(type: "INTEGER", nullable: false),
                    Truncated = table.Column<bool>(type: "INTEGER", nullable: false),
                    ReceivedCount = table.Column<int>(type: "INTEGER", nullable: false),
                    LogsJson = table.Column<string>(type: "TEXT", nullable: false),
                    ReceivedAtUtc = table.Column<DateTimeOffset>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_log_batches", x => x.Id);
                    table.ForeignKey(
                        name: "FK_log_batches_devices_DeviceRecordId",
                        column: x => x.DeviceRecordId,
                        principalTable: "devices",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_devices_DeviceId",
                table: "devices",
                column: "DeviceId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_heartbeats_DeviceRecordId",
                table: "heartbeats",
                column: "DeviceRecordId");

            migrationBuilder.CreateIndex(
                name: "IX_log_batches_DeviceRecordId",
                table: "log_batches",
                column: "DeviceRecordId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "heartbeats");

            migrationBuilder.DropTable(
                name: "log_batches");

            migrationBuilder.DropTable(
                name: "devices");
        }
    }
}
