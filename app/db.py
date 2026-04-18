"""SQLite connection helper + additive migrations for forgetting-curve analytics."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "sprint.db"

# Additive migration: create new tables on startup if missing. Does NOT touch
# spec-mandated tables (FlashcardPages, SprintSessions, LearningJourney_Map).
MIGRATION_SQL = """
CREATE TABLE IF NOT EXISTS Agents (
    agent_id        TEXT    PRIMARY KEY,
    employee_code   TEXT    UNIQUE,
    display_name    TEXT    NOT NULL,
    email           TEXT,
    team            TEXT,
    role            TEXT,
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS ChapterMastery (
    mastery_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id                TEXT    NOT NULL,
    module_id               INTEGER NOT NULL,
    first_read_at           TEXT,
    last_read_at            TEXT,
    total_valid_sprints     INTEGER DEFAULT 0,
    total_timed_out         INTEGER DEFAULT 0,
    total_abandoned         INTEGER DEFAULT 0,
    best_score_pct          REAL    DEFAULT 0,
    last_score_pct          REAL,
    avg_tab_switches        REAL    DEFAULT 0,
    ease_factor             REAL    DEFAULT 2.5,
    current_interval_days   REAL    DEFAULT 1,
    next_review_at          TEXT,
    retention_estimate      REAL    DEFAULT 1.0,
    status                  TEXT    DEFAULT 'new',
    updated_at              TEXT    NOT NULL,
    UNIQUE(agent_id, module_id),
    FOREIGN KEY (agent_id) REFERENCES Agents(agent_id),
    FOREIGN KEY (module_id) REFERENCES MicroModules(module_id)
);

CREATE TABLE IF NOT EXISTS ReviewEvents (
    event_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id         TEXT    NOT NULL,
    module_id        INTEGER NOT NULL,
    event_type       TEXT    NOT NULL,
    sprint_id        TEXT,
    quiz_session_id  TEXT,
    score_pct        REAL,
    reading_seconds  INTEGER,
    tab_switch_count INTEGER,
    recall_quality   INTEGER,
    event_timestamp  TEXT    NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES Agents(agent_id),
    FOREIGN KEY (module_id) REFERENCES MicroModules(module_id)
);

CREATE INDEX IF NOT EXISTS idx_review_events_agent_time
    ON ReviewEvents(agent_id, event_timestamp);
CREATE INDEX IF NOT EXISTS idx_review_events_module
    ON ReviewEvents(module_id);
"""

# Default agent seed — agent_id is used internally (stable surrogate key),
# employee_code is the business-facing ID shown in the UI / sent to the
# Secure Data Gateway (which will tokenize it into token_id).
DEFAULT_AGENT_ID = "demo-agent-001"
DEFAULT_AGENT_NAME = "葉悟員"
DEFAULT_EMPLOYEE_CODE = "KGI-MA-2026-042"  # 凱基-MA訓練生-2026年第42號


def init_migrations():
    """Called once at app startup. Idempotent."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(MIGRATION_SQL)
        # Add employee_code column if upgrading from older Agents schema
        try:
            conn.execute("ALTER TABLE Agents ADD COLUMN employee_code TEXT")
        except sqlite3.OperationalError:
            pass  # already exists
        try:
            conn.execute("ALTER TABLE Agents ADD COLUMN role TEXT")
        except sqlite3.OperationalError:
            pass
        # Seed default agent if missing
        row = conn.execute(
            "SELECT agent_id FROM Agents WHERE agent_id = ?", (DEFAULT_AGENT_ID,)
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO Agents (agent_id, employee_code, display_name, email, "
                "team, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (DEFAULT_AGENT_ID, DEFAULT_EMPLOYEE_CODE, DEFAULT_AGENT_NAME,
                 "yewuyuan@kgifh.internal", "個人金融事業群 · 數位金融",
                 "MA 管理培訓生",
                 datetime.now(timezone.utc).isoformat()),
            )
        else:
            # Backfill the new fields on existing row
            conn.execute(
                "UPDATE Agents SET employee_code = COALESCE(employee_code, ?), "
                "email = COALESCE(email, ?), team = COALESCE(team, ?), "
                "role = COALESCE(role, ?) WHERE agent_id = ?",
                (DEFAULT_EMPLOYEE_CODE, "yewuyuan@kgifh.internal",
                 "個人金融事業群 · 數位金融", "MA 管理培訓生", DEFAULT_AGENT_ID),
            )
        conn.commit()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
