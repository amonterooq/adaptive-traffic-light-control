PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    scenario TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('fijo','adaptativo')),
    seed INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('running','complete','cancelled','failed')),
    config_json TEXT NOT NULL,
    summary_json TEXT
);
CREATE TABLE IF NOT EXISTS samples (
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    t INTEGER NOT NULL CHECK(t >= 0),
    q_n INTEGER NOT NULL CHECK(q_n >= 0),
    q_e INTEGER NOT NULL CHECK(q_e >= 0),
    q_s INTEGER NOT NULL CHECK(q_s >= 0),
    q_w INTEGER NOT NULL CHECK(q_w >= 0),
    state TEXT NOT NULL CHECK(state IN ('GrGr','rGrG','yryr','ryry','rrrr','GGGG','yyyy')),
    fallback INTEGER NOT NULL CHECK(fallback IN (0,1)),
    arrived INTEGER NOT NULL,
    in_network INTEGER NOT NULL,
    PRIMARY KEY (run_id,t)
);
CREATE TABLE IF NOT EXISTS pedestrian_samples (
    run_id TEXT NOT NULL,
    t INTEGER NOT NULL,
    ped_signal TEXT NOT NULL CHECK(ped_signal IN ('G','r')),
    ped_waiting INTEGER NOT NULL CHECK(ped_waiting >= 0),
    ped_crossing INTEGER NOT NULL CHECK(ped_crossing >= 0),
    ped_stage TEXT NOT NULL,
    PRIMARY KEY (run_id,t),
    FOREIGN KEY (run_id,t) REFERENCES samples(run_id,t) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cooperative_samples (
    run_id TEXT NOT NULL,
    t INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (run_id,t),
    FOREIGN KEY (run_id,t) REFERENCES samples(run_id,t) ON DELETE CASCADE
);
PRAGMA user_version = 4;
