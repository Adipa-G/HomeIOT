using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace HomeIOT.Api.Migrations
{
    /// <inheritdoc />
    public partial class FixUnsyncedModuleResultTimestamps : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Results recorded before the device synced its clock carry a default date
            // (2021-01-01 on rp2). Re-date them to when the server received them so they sort
            // and chart correctly. Timestamps are stored as "yyyy-MM-dd HH:mm:ss...+00:00" text.
            migrationBuilder.Sql(
                "UPDATE module_results " +
                "SET StartedAtUtc = ReceivedAtUtc, FinishedAtUtc = ReceivedAtUtc " +
                "WHERE StartedAtUtc < '2024-01-01' OR FinishedAtUtc < '2024-01-01';");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            // The original device timestamps are not recoverable.
        }
    }
}