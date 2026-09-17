CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Convert high-volume telemetry into a time-series hypertable in production.
-- The ORM creates the table before this script is applied by the deployment job.
-- SELECT create_hypertable('telemetry', by_range('recorded_at'), if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS ix_telemetry_asset_time ON telemetry (asset_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS ix_alerts_status_created ON alerts (status, created_at DESC);
