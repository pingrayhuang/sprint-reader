"""Forgetting-curve (Ebbinghaus / SM-2 lite) mastery tracker.

Two concerns:
  1. ReviewEvents — append-only log (every learning touchpoint; for data scientists).
  2. ChapterMastery — per-agent × per-module aggregated state (for app UI + recommendations).

Design philosophy: spec-mandated tables (SprintSessions / LearningJourney_Map)
are NOT modified. All learning-science metadata lives in NEW tables.
"""
from datetime import datetime, timedelta, timezone

from app.db import get_conn


# --- SM-2-lite: map quiz score pct -> recall quality 0..5 ---
def score_to_quality(score_pct: float) -> int:
    if score_pct >= 100: return 5
    if score_pct >= 85:  return 4
    if score_pct >= 70:  return 3
    if score_pct >= 50:  return 2
    if score_pct >= 30:  return 1
    return 0


def next_ease(prev_ef: float, quality: int) -> float:
    """SM-2 update rule, clamped to [1.3, 3.0]."""
    new_ef = prev_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return max(1.3, min(3.0, new_ef))


def next_interval(prev_interval_days: float, ease: float, quality: int) -> float:
    if quality < 3:
        return 1.0  # reset if recall failed
    if prev_interval_days < 1:
        return 1.0
    if prev_interval_days < 6:
        return 6.0
    return round(prev_interval_days * ease, 2)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_event(
    agent_id: str,
    module_id: int,
    event_type: str,
    sprint_id: str | None = None,
    quiz_session_id: str | None = None,
    score_pct: float | None = None,
    reading_seconds: int | None = None,
    tab_switch_count: int | None = None,
    recall_quality: int | None = None,
):
    """Append-only. Never UPDATE / DELETE these rows."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO ReviewEvents (agent_id, module_id, event_type, sprint_id, "
            "quiz_session_id, score_pct, reading_seconds, tab_switch_count, "
            "recall_quality, event_timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (agent_id, module_id, event_type, sprint_id, quiz_session_id,
             score_pct, reading_seconds, tab_switch_count, recall_quality, _now_iso()),
        )
        conn.commit()


def update_mastery_after_quiz(
    agent_id: str, module_id: int, score_pct: float,
    reading_seconds: int | None, tab_switch_count: int | None,
):
    """Upsert ChapterMastery after a valid finished_early sprint + quiz.

    Uses SM-2 lite: update ease_factor, compute next_review_at.
    """
    quality = score_to_quality(score_pct)
    now = _now_iso()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM ChapterMastery WHERE agent_id = ? AND module_id = ?",
            (agent_id, module_id),
        ).fetchone()
        if not row:
            ease = next_ease(2.5, quality)
            interval = next_interval(0, ease, quality)
            next_review = (datetime.now(timezone.utc) + timedelta(days=interval)).isoformat()
            conn.execute(
                "INSERT INTO ChapterMastery (agent_id, module_id, first_read_at, last_read_at, "
                "total_valid_sprints, best_score_pct, last_score_pct, avg_tab_switches, "
                "ease_factor, current_interval_days, next_review_at, retention_estimate, "
                "status, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, 1.0, ?, ?)",
                (agent_id, module_id, now, now, score_pct, score_pct,
                 float(tab_switch_count or 0), ease, interval, next_review,
                 "review" if quality >= 3 else "learning", now),
            )
        else:
            prev_ef = row["ease_factor"] or 2.5
            prev_int = row["current_interval_days"] or 1.0
            new_ef = next_ease(prev_ef, quality)
            new_int = next_interval(prev_int, new_ef, quality)
            new_next = (datetime.now(timezone.utc) + timedelta(days=new_int)).isoformat()
            n = (row["total_valid_sprints"] or 0) + 1
            prev_avg = row["avg_tab_switches"] or 0
            new_avg_tab = (prev_avg * (n - 1) + (tab_switch_count or 0)) / n
            new_best = max(row["best_score_pct"] or 0, score_pct)
            new_status = "mastered" if (new_best >= 90 and new_int >= 14) else ("review" if quality >= 3 else "learning")
            conn.execute(
                "UPDATE ChapterMastery SET last_read_at=?, total_valid_sprints=?, "
                "best_score_pct=?, last_score_pct=?, avg_tab_switches=?, ease_factor=?, "
                "current_interval_days=?, next_review_at=?, retention_estimate=1.0, "
                "status=?, updated_at=? WHERE agent_id=? AND module_id=?",
                (now, n, new_best, score_pct, new_avg_tab, new_ef, new_int,
                 new_next, new_status, now, agent_id, module_id),
            )
        conn.commit()


def record_invalid_sprint(agent_id: str, module_id: int, sprint_id: str, status: str,
                          tab_switch_count: int | None):
    """For timed_out / abandoned: increment the counter, don't affect mastery."""
    col = "total_timed_out" if status == "timed_out" else "total_abandoned"
    now = _now_iso()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT mastery_id FROM ChapterMastery WHERE agent_id = ? AND module_id = ?",
            (agent_id, module_id),
        ).fetchone()
        if not row:
            conn.execute(
                f"INSERT INTO ChapterMastery (agent_id, module_id, {col}, updated_at) "
                f"VALUES (?, ?, 1, ?)",
                (agent_id, module_id, now),
            )
        else:
            conn.execute(
                f"UPDATE ChapterMastery SET {col} = COALESCE({col}, 0) + 1, updated_at = ? "
                f"WHERE agent_id = ? AND module_id = ?",
                (now, agent_id, module_id),
            )
        conn.commit()
    record_event(
        agent_id=agent_id, module_id=module_id,
        event_type=f"sprint_{status}", sprint_id=sprint_id,
        tab_switch_count=tab_switch_count,
    )
