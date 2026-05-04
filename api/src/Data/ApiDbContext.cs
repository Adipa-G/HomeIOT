using HomeIOT.Api.Data.Entities;
using Microsoft.EntityFrameworkCore;

namespace HomeIOT.Api.Data;

public sealed class ApiDbContext(DbContextOptions<ApiDbContext> options) : DbContext(options)
{
    public DbSet<DeviceRecord> Devices => Set<DeviceRecord>();
    public DbSet<HeartbeatRecord> Heartbeats => Set<HeartbeatRecord>();
    public DbSet<LogBatchRecord> LogBatches => Set<LogBatchRecord>();
    public DbSet<UserRecord> Users => Set<UserRecord>();
    public DbSet<ModuleDefinitionRecord> ModuleDefinitions => Set<ModuleDefinitionRecord>();
    public DbSet<ModuleVersionRecord> ModuleVersions => Set<ModuleVersionRecord>();
    public DbSet<ModuleAssignmentRecord> ModuleAssignments => Set<ModuleAssignmentRecord>();
    public DbSet<ModuleResultRecord> ModuleResults => Set<ModuleResultRecord>();
    public DbSet<ModuleStatusRecord> ModuleStatuses => Set<ModuleStatusRecord>();
    public DbSet<ModuleVariableDefRecord> ModuleVariableDefs => Set<ModuleVariableDefRecord>();
    public DbSet<ModuleVariableValueRecord> ModuleVariableValues => Set<ModuleVariableValueRecord>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // SQLite stores DateTimeOffset as TEXT (ISO 8601) but the EF Core SQLite
        // provider cannot translate DateTimeOffset comparisons or ORDER BY.
        // Tell EF to treat them as strings so comparisons and ordering translate
        // to simple TEXT operations which work correctly with ISO 8601 format.
        foreach (var entityType in modelBuilder.Model.GetEntityTypes())
        {
            foreach (var property in entityType.GetProperties())
            {
                if (property.ClrType == typeof(DateTimeOffset))
                    property.SetValueConverter(new Microsoft.EntityFrameworkCore.Storage.ValueConversion.DateTimeOffsetToStringConverter());
                else if (property.ClrType == typeof(DateTimeOffset?))
                    property.SetValueConverter(new Microsoft.EntityFrameworkCore.Storage.ValueConversion.DateTimeOffsetToStringConverter());
            }
        }

        modelBuilder.Entity<DeviceRecord>(entity =>
        {
            entity.ToTable("devices");
            entity.HasKey(x => x.Id);
            entity.Property(x => x.DeviceId).HasMaxLength(128).IsRequired();
            entity.Property(x => x.ApiKey).HasMaxLength(512).IsRequired();
            entity.Property(x => x.Platform).HasMaxLength(32);
            entity.Property(x => x.Version).HasMaxLength(64);
            entity.Property(x => x.Ip).HasMaxLength(128);
            entity.Property(x => x.Mode).HasMaxLength(32).HasDefaultValue("production");
            entity.HasIndex(x => x.DeviceId).IsUnique();
        });

        modelBuilder.Entity<HeartbeatRecord>(entity =>
        {
            entity.ToTable("heartbeats");
            entity.HasKey(x => x.Id);
            entity.HasOne(x => x.Device)
                .WithMany(x => x.Heartbeats)
                .HasForeignKey(x => x.DeviceRecordId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<LogBatchRecord>(entity =>
        {
            entity.ToTable("log_batches");
            entity.HasKey(x => x.Id);
            entity.Property(x => x.Reason).HasMaxLength(64).IsRequired();
            entity.Property(x => x.LogsJson).IsRequired();
            entity.HasOne(x => x.Device)
                .WithMany(x => x.LogBatches)
                .HasForeignKey(x => x.DeviceRecordId)
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<UserRecord>(entity =>
        {
            entity.ToTable("users");
            entity.HasKey(x => x.Id);
            entity.Property(x => x.Username).HasMaxLength(128).IsRequired();
            entity.Property(x => x.PasswordHash).HasMaxLength(512).IsRequired();
            entity.HasIndex(x => x.Username).IsUnique();
        });

        modelBuilder.Entity<ModuleDefinitionRecord>(entity =>
        {
            entity.ToTable("module_definitions");
            entity.HasKey(x => x.Id);
            entity.Property(x => x.ModuleId).HasMaxLength(128).IsRequired();
            entity.Property(x => x.Description).HasMaxLength(1024);
            entity.Property(x => x.DefaultEntrypoint).HasMaxLength(128).HasDefaultValue("run");
            entity.HasIndex(x => x.ModuleId).IsUnique();
        });

        modelBuilder.Entity<ModuleVersionRecord>(entity =>
        {
            entity.ToTable("module_versions");
            entity.HasKey(x => x.Id);
            entity.Property(x => x.Version).HasMaxLength(64).IsRequired();
            entity.Property(x => x.PackageHash).HasMaxLength(128).IsRequired();
            entity.HasOne(x => x.ModuleDefinition)
                .WithMany(x => x.Versions)
                .HasForeignKey(x => x.ModuleDefinitionId)
                .OnDelete(DeleteBehavior.Cascade);
            entity.HasIndex(x => new { x.ModuleDefinitionId, x.Version }).IsUnique();
        });

        modelBuilder.Entity<ModuleAssignmentRecord>(entity =>
        {
            entity.ToTable("module_assignments");
            entity.HasKey(x => x.Id);
            entity.Property(x => x.Entrypoint).HasMaxLength(128).HasDefaultValue("run");
            entity.HasOne(x => x.Device)
                .WithMany()
                .HasForeignKey(x => x.DeviceRecordId)
                .OnDelete(DeleteBehavior.Cascade);
            entity.HasOne(x => x.ModuleDefinition)
                .WithMany(x => x.Assignments)
                .HasForeignKey(x => x.ModuleDefinitionId)
                .OnDelete(DeleteBehavior.Cascade);
            entity.HasOne(x => x.ModuleVersion)
                .WithMany()
                .HasForeignKey(x => x.ModuleVersionId)
                .OnDelete(DeleteBehavior.Cascade);
            entity.HasIndex(x => new { x.DeviceRecordId, x.ModuleDefinitionId }).IsUnique();
        });

        modelBuilder.Entity<ModuleResultRecord>(entity =>
        {
            entity.ToTable("module_results");
            entity.HasKey(x => x.Id);
            entity.Property(x => x.DeviceId).HasMaxLength(128).IsRequired();
            entity.Property(x => x.ModuleId).HasMaxLength(128).IsRequired();
            entity.Property(x => x.ModuleVersion).HasMaxLength(64).IsRequired();
            entity.Property(x => x.RunId).HasMaxLength(256).IsRequired();
            entity.Property(x => x.Status).HasMaxLength(32).IsRequired();
            entity.HasIndex(x => new { x.DeviceId, x.ModuleId });
        });

        modelBuilder.Entity<ModuleStatusRecord>(entity =>
        {
            entity.ToTable("module_statuses");
            entity.HasKey(x => x.Id);
            entity.Property(x => x.DeviceId).HasMaxLength(128).IsRequired();
            entity.Property(x => x.ModuleId).HasMaxLength(128).IsRequired();
            entity.Property(x => x.ModuleVersion).HasMaxLength(64).IsRequired();
            entity.Property(x => x.DisabledReason).HasMaxLength(512);
            entity.HasIndex(x => new { x.DeviceId, x.ModuleId });
        });

        modelBuilder.Entity<ModuleVariableDefRecord>(entity =>
        {
            entity.ToTable("module_variable_defs");
            entity.HasKey(x => x.Id);
            entity.Property(x => x.Name).HasMaxLength(64).IsRequired();
            entity.Property(x => x.Type).HasMaxLength(16).HasDefaultValue("string").IsRequired();
            entity.Property(x => x.DefaultValue).HasMaxLength(1024);
            entity.Property(x => x.Description).HasMaxLength(512);
            entity.HasOne(x => x.ModuleDefinition)
                .WithMany(x => x.VariableDefs)
                .HasForeignKey(x => x.ModuleDefinitionId)
                .OnDelete(DeleteBehavior.Cascade);
            entity.HasIndex(x => new { x.ModuleDefinitionId, x.Name }).IsUnique();
        });

        modelBuilder.Entity<ModuleVariableValueRecord>(entity =>
        {
            entity.ToTable("module_variable_values");
            entity.HasKey(x => x.Id);
            entity.Property(x => x.VariableName).HasMaxLength(64).IsRequired();
            entity.Property(x => x.Value).HasMaxLength(1024);
            entity.HasOne(x => x.ModuleAssignment)
                .WithMany(x => x.VariableValues)
                .HasForeignKey(x => x.ModuleAssignmentId)
                .OnDelete(DeleteBehavior.Cascade);
            entity.HasIndex(x => new { x.ModuleAssignmentId, x.VariableName }).IsUnique();
        });
    }
}
