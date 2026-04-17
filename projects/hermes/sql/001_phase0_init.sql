CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS viewers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE,
    display_name TEXT,
    training_background JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50),
    payload_type TEXT,
    payload_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coordinate VARCHAR(20) UNIQUE NOT NULL,
    target_id UUID NOT NULL REFERENCES targets(id) ON DELETE RESTRICT,
    blinding_mode VARCHAR(20) NOT NULL DEFAULT 'double-blind',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
    viewer_id UUID NOT NULL REFERENCES viewers(id) ON DELETE RESTRICT,
    primary_measurement INT CHECK (primary_measurement BETWEEN 0 AND 100),
    auxiliary_parameters JSONB DEFAULT '{}'::jsonb,
    subjective_notes TEXT,
    confidence_rating INT CHECK (confidence_rating BETWEEN 0 AND 100),
    local_sidereal_time NUMERIC,
    solar_weather_index JSONB DEFAULT '{}'::jsonb,
    moon_phase VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_targets_category ON targets(category);
CREATE INDEX IF NOT EXISTS idx_tasks_target_id ON tasks(target_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_sessions_task_id ON sessions(task_id);
CREATE INDEX IF NOT EXISTS idx_sessions_viewer_id ON sessions(viewer_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);
