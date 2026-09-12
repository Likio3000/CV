CREATE TABLE IF NOT EXISTS readings (
    reading_id TEXT PRIMARY KEY,
    machine_id TEXT NOT NULL,
    event_time INTEGER NOT NULL,
    available_at INTEGER NOT NULL,
    temperature_milli_c INTEGER NOT NULL,
    vibration_milli_mm_s INTEGER NOT NULL,
    digest TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS readings_as_of ON readings(machine_id, event_time, available_at);
CREATE TABLE IF NOT EXISTS quarantine (
    digest TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS training_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    manifest TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS online_features (
    machine_id TEXT PRIMARY KEY,
    feature_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS online_generation (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    as_of INTEGER NOT NULL,
    definition_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS online_quality (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    report_json TEXT NOT NULL
);
