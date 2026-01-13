SET TIME ZONE 'UTC';

CREATE TABLE earthquake_activity (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    raw JSONB NOT NULL,
    dt TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE sensor_tectonic_stress (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    raw JSONB NOT NULL,
    dt TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE earthquake_activity_with_stress (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    raw JSONB NOT NULL,
    dt TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    average_tectonic_stress_magnitude FLOAT,
    dt_ingested_prev_catostrophic TIMESTAMP WITH TIME ZONE,
    dt_recorded_prev_catastrophic TIMESTAMP
);
