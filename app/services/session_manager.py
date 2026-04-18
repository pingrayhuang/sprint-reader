"""Sprint session lifecycle. Server-authoritative timestamps prevent client-side timer tampering."""
import uuid
from datetime import datetime, timezone
from app.db import get_conn

VALID_END_STATUS = {"finished_early", "timed_out", "abandoned"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_sprint(agent_id: str, module_id: int) -> dict:
    sprint_id = str(uuid.uuid4())
    started = _now_iso()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO SprintSessions (sprint_id, agent_id, module_id, start_timestamp, "
            "tab_switch_count, completion_status) VALUES (?, ?, ?, ?, 0, 'in_progress')",
            (sprint_id, agent_id, module_id, started),
        )
    return {"sprint_id": sprint_id, "start_timestamp": started}


def increment_tab_switch(sprint_id: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE SprintSessions SET tab_switch_count = tab_switch_count + 1 "
            "WHERE sprint_id = ? AND completion_status = 'in_progress' RETURNING tab_switch_count",
            (sprint_id,),
        )
        row = cur.fetchone()
    if not row:
        raise ValueError(f"sprint {sprint_id} not found or already closed")
    return row["tab_switch_count"]


def complete_sprint(sprint_id: str, status: str) -> dict:
    if status not in VALID_END_STATUS:
        raise ValueError(f"invalid status: {status}")
    ended = _now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE SprintSessions SET end_timestamp = ?, completion_status = ? "
            "WHERE sprint_id = ? AND completion_status = 'in_progress' "
            "RETURNING agent_id, module_id, start_timestamp, tab_switch_count",
            (ended, status, sprint_id),
        )
        row = cur.fetchone()
    if not row:
        raise ValueError(f"sprint {sprint_id} not found or already closed")
    duration = (datetime.fromisoformat(ended) - datetime.fromisoformat(row["start_timestamp"])).total_seconds()

    # Forgetting-curve analytics: log invalid sprints (timed_out / abandoned)
    # so data scientists can analyze drop-off / attention patterns.
    if status in ("timed_out", "abandoned"):
        from app.services import mastery
        mastery.record_invalid_sprint(
            agent_id=row["agent_id"],
            module_id=row["module_id"],
            sprint_id=sprint_id,
            status=status,
            tab_switch_count=row["tab_switch_count"],
        )

    return {
        "sprint_id": sprint_id,
        "end_timestamp": ended,
        "completion_status": status,
        "tab_switch_count": row["tab_switch_count"],
        "duration_sec": round(duration, 2),
    }


def get_sprint(sprint_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM SprintSessions WHERE sprint_id = ?", (sprint_id,)).fetchone()
    return dict(row) if row else None
