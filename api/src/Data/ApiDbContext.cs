using HomeIOT.Api.Data.Entities;
using Microsoft.EntityFrameworkCore;

namespace HomeIOT.Api.Data;

public sealed class ApiDbContext(DbContextOptions<ApiDbContext> options) : DbContext(options)
{
    public DbSet<DeviceRecord> Devices => Set<DeviceRecord>();
    public DbSet<HeartbeatRecord> Heartbeats => Set<HeartbeatRecord>();
    public DbSet<LogBatchRecord> LogBatches => Set<LogBatchRecord>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
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
    }
}
