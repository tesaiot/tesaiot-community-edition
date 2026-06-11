-- SPDX-License-Identifier: Apache-2.0
-- TESAIoT Community Edition — TimescaleDB initialization
-- Origin: TESAIoT Secure IoT Platform. Contributors: TESAIoT Platform contributors.
--
-- Single-organization distribution. The organization_id columns are retained so
-- application queries/indexes keep working, but CE always writes a single
-- default org id (see DEFAULT_ORG_ID in the API config).
--
-- This schema backs the IoT Telemetry Dashboard inside Device Details.

-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- DEVICE TELEMETRY (powers the IoT Telemetry Dashboard)
-- ============================================================================
CREATE TABLE IF NOT EXISTS device_telemetry (
    time TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(50),
    location JSONB,
    metadata JSONB
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('device_telemetry', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_telemetry_device_time ON device_telemetry (device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_org_time ON device_telemetry (organization_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_metric ON device_telemetry (metric_name, time DESC);

-- Continuous aggregate for real-time dashboards
CREATE MATERIALIZED VIEW IF NOT EXISTS device_metrics_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    device_id,
    metric_name,
    AVG(metric_value) as avg_value,
    MIN(metric_value) as min_value,
    MAX(metric_value) as max_value,
    COUNT(*) as sample_count
FROM device_telemetry
GROUP BY bucket, device_id, metric_name
WITH NO DATA;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('device_metrics_1min',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '1 minute');

-- ============================================================================
-- DEVICE EVENTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS device_events (
    time TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT,
    details JSONB
);

-- Convert events to hypertable
SELECT create_hypertable('device_events', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Retention policies
SELECT add_retention_policy('device_telemetry', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('device_events', INTERVAL '180 days', if_not_exists => TRUE);

-- ============================================================================
-- AUDIT TRAIL (optional)
-- Kept for the user/device audit-trail feature. Drop these two blocks if the
-- audit trail is not needed; nothing else in CE depends on them.
-- ============================================================================

-- Activity logs table for user actions
CREATE TABLE IF NOT EXISTS activity_logs (
    id BIGSERIAL,
    time TIMESTAMPTZ NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    result VARCHAR(20) NOT NULL,
    duration_ms INTEGER,
    client_ip INET,
    user_agent TEXT,
    metadata JSONB,
    PRIMARY KEY (time, id)
);

SELECT create_hypertable('activity_logs', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_activity_user_time ON activity_logs (user_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_activity_org_time ON activity_logs (organization_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_activity_action_time ON activity_logs (action, time DESC);
CREATE INDEX IF NOT EXISTS idx_activity_resource ON activity_logs (resource_type, resource_id) WHERE resource_type IS NOT NULL;

-- Security logs table for security events
CREATE TABLE IF NOT EXISTS security_logs (
    id BIGSERIAL,
    time TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    user_id VARCHAR(50),
    organization_id VARCHAR(50),
    source_ip INET,
    target_resource VARCHAR(255),
    action_taken VARCHAR(100),
    threat_score INTEGER,
    details JSONB,
    PRIMARY KEY (time, id)
);

SELECT create_hypertable('security_logs', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_security_severity_time ON security_logs (severity, time DESC);
CREATE INDEX IF NOT EXISTS idx_security_event_time ON security_logs (event_type, time DESC);
CREATE INDEX IF NOT EXISTS idx_security_user_time ON security_logs (user_id, time DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_security_ip ON security_logs (source_ip) WHERE source_ip IS NOT NULL;

-- Retention policies for audit logs
SELECT add_retention_policy('activity_logs', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('security_logs', INTERVAL '180 days', if_not_exists => TRUE);

-- ============================================================================
-- Grant permissions to the application user
-- ============================================================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
