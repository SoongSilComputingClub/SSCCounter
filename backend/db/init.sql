CREATE SCHEMA IF NOT EXISTS admin;
CREATE SCHEMA IF NOT EXISTS dashboard;

CREATE TABLE IF NOT EXISTS admin.capture_logs (
    id BIGSERIAL PRIMARY KEY,

    measured_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    people_count INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'success',
    trigger_type VARCHAR(20) NOT NULL DEFAULT 'scheduled',

    inference_time_ms INTEGER,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_capture_logs_measured_at
ON admin.capture_logs (measured_at DESC);

CREATE INDEX IF NOT EXISTS idx_capture_logs_status_measured_at
ON admin.capture_logs (status, measured_at DESC);

CREATE TABLE IF NOT EXISTS dashboard.current_status (
    id SMALLINT PRIMARY KEY DEFAULT 1,

    current_people_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ,

    today_max_people_count INTEGER NOT NULL DEFAULT 0,
    today_avg_people_count NUMERIC(5,2) NOT NULL DEFAULT 0,

    CONSTRAINT only_one_current_status CHECK (id = 1)
);

INSERT INTO dashboard.current_status (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS dashboard.today_hourly_stats (
    stat_date DATE NOT NULL,
    hour INTEGER NOT NULL,

    avg_people_count NUMERIC(5,2) NOT NULL DEFAULT 0,
    max_people_count INTEGER NOT NULL DEFAULT 0,
    sample_count INTEGER NOT NULL DEFAULT 0,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (stat_date, hour),
    CONSTRAINT valid_today_hour CHECK (hour BETWEEN 0 AND 23)
);

CREATE TABLE IF NOT EXISTS dashboard.daily_stats (
    stat_date DATE PRIMARY KEY,

    avg_people_count NUMERIC(5,2) NOT NULL DEFAULT 0,
    max_people_count INTEGER NOT NULL DEFAULT 0,
    min_people_count INTEGER NOT NULL DEFAULT 0,

    peak_hour INTEGER,
    quiet_hour INTEGER,

    sample_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT valid_peak_hour CHECK (peak_hour IS NULL OR peak_hour BETWEEN 0 AND 23),
    CONSTRAINT valid_quiet_hour CHECK (quiet_hour IS NULL OR quiet_hour BETWEEN 0 AND 23)
);

CREATE TABLE IF NOT EXISTS dashboard.weekday_hourly_stats (
    weekday INTEGER NOT NULL,
    hour INTEGER NOT NULL,

    avg_people_count NUMERIC(5,2) NOT NULL DEFAULT 0,
    max_people_count INTEGER NOT NULL DEFAULT 0,
    sample_count INTEGER NOT NULL DEFAULT 0,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (weekday, hour),
    CONSTRAINT valid_weekday CHECK (weekday BETWEEN 1 AND 5),
    CONSTRAINT valid_weekday_hour CHECK (hour BETWEEN 9 AND 22)
);
