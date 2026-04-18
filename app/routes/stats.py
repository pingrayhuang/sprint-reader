"""Aggregate stats: study streak, daily heatmap, per-chapter completion, wrong-answer review."""
import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter
from app.db import get_conn

router = APIRouter(prefix="/api/stats", tags=["stats"])

DAYS = 28  # 4-week heatmap


@router.get("/progress")
def progress(agent_id: str = "demo-agent-001"):
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=DAYS - 1)
    # Exclude timed_out + abandoned: these are "invalid" sessions per spec requirement
    # (user timed out or closed the tab without finishing the 7-min sprint)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date(start_timestamp) AS d, COUNT(*) AS c, "
            "SUM(CAST((julianday(end_timestamp) - julianday(start_timestamp)) * 86400 AS INTEGER)) AS secs "
            "FROM SprintSessions "
            "WHERE agent_id = ? AND end_timestamp IS NOT NULL "
            "  AND completion_status = 'finished_early' "
            "  AND date(start_timestamp) >= ? "
            "GROUP BY date(start_timestamp) ORDER BY d",
            (agent_id, start_date.isoformat()),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) AS c, "
            "SUM(CAST((julianday(end_timestamp) - julianday(start_timestamp)) * 86400 AS INTEGER)) AS secs "
            "FROM SprintSessions WHERE agent_id = ? AND end_timestamp IS NOT NULL "
            "  AND completion_status = 'finished_early'",
            (agent_id,),
        ).fetchone()
        score_row = conn.execute(
            "SELECT AVG(CAST(score AS FLOAT) / total_questions) AS avg_pct, COUNT(*) AS n "
            "FROM LearningJourney_Map j JOIN SprintSessions s ON j.sprint_id = s.sprint_id "
            "WHERE s.agent_id = ? AND j.score IS NOT NULL",
            (agent_id,),
        ).fetchone()

    by_date = {r["d"]: {"count": r["c"], "secs": r["secs"] or 0} for r in rows}
    days = []
    for i in range(DAYS):
        d = start_date + timedelta(days=i)
        key = d.isoformat()
        info = by_date.get(key, {"count": 0, "secs": 0})
        days.append({
            "date": key,
            "dow": d.isoweekday(),  # 1=Mon .. 7=Sun
            "count": info["count"],
            "minutes": round(info["secs"] / 60, 1),
        })

    # Current streak: consecutive days ending at today with at least 1 sprint
    current_streak = 0
    for d in reversed(days):
        if d["count"] > 0:
            current_streak += 1
        else:
            break
    # Longest streak in window
    longest = cur = 0
    for d in days:
        cur = cur + 1 if d["count"] > 0 else 0
        longest = max(longest, cur)

    return {
        "today": today.isoformat(),
        "window_days": DAYS,
        "total_sprints": total["c"] or 0,
        "total_minutes": round((total["secs"] or 0) / 60, 1),
        "avg_score_pct": round((score_row["avg_pct"] or 0) * 100, 1),
        "current_streak": current_streak,
        "longest_streak": longest,
        "days": days,
    }


@router.get("/chapters")
def chapter_completion(agent_id: str = "demo-agent-001"):
    """Per-chapter completion: how many sprints + avg score + wrong-answer count."""
    with get_conn() as conn:
        mods = conn.execute(
            "SELECT module_id, title, sort_order FROM MicroModules ORDER BY sort_order"
        ).fetchall()
        out = []
        all_done = True
        for m in mods:
            sprints = conn.execute(
                "SELECT COUNT(*) AS c FROM SprintSessions WHERE agent_id = ? AND module_id = ? "
                "AND end_timestamp IS NOT NULL AND completion_status = 'finished_early'",
                (agent_id, m["module_id"]),
            ).fetchone()["c"]
            scores = conn.execute(
                "SELECT j.score, j.total_questions FROM LearningJourney_Map j "
                "JOIN SprintSessions s ON j.sprint_id = s.sprint_id "
                "WHERE s.agent_id = ? AND s.module_id = ? AND j.score IS NOT NULL",
                (agent_id, m["module_id"]),
            ).fetchall()
            best_pct = 0.0
            avg_pct = 0.0
            if scores:
                pcts = [r["score"] / r["total_questions"] for r in scores if r["total_questions"]]
                if pcts:
                    best_pct = max(pcts) * 100
                    avg_pct = sum(pcts) / len(pcts) * 100
            wrong = conn.execute(
                "SELECT COUNT(*) AS c FROM QuizResponses r "
                "JOIN QuizQuestions q ON r.question_id = q.question_id "
                "WHERE q.module_id = ? AND r.is_correct = 0",
                (m["module_id"],),
            ).fetchone()["c"]
            completed = bool(scores)
            if not completed:
                all_done = False
            out.append({
                "module_id": m["module_id"],
                "title": m["title"],
                "sort_order": m["sort_order"],
                "sprints": sprints,
                "best_score_pct": round(best_pct, 1),
                "avg_score_pct": round(avg_pct, 1),
                "wrong_count": wrong,
                "completed": completed,
            })
        completed_count = sum(1 for c in out if c["completed"])
        overall_pct = round(100 * completed_count / len(out), 1) if out else 0
        overall_avg = round(sum(c["avg_score_pct"] for c in out) / len(out), 1) if out else 0
    return {
        "chapters": out,
        "total_chapters": len(out),
        "completed_chapters": completed_count,
        "overall_completion_pct": overall_pct,
        "overall_avg_score_pct": overall_avg,
        "all_done": all_done,
    }


@router.get("/recommend")
def recommend(agent_id: str = "demo-agent-001"):
    """Today's recommended chapter based on: wrong-rate * 0.6 + days-since * 0.4.
    Never-read chapter gets score 20. Picks highest score."""
    today = datetime.now(timezone.utc).date()
    with get_conn() as conn:
        mods = conn.execute(
            "SELECT module_id, title FROM MicroModules ORDER BY sort_order"
        ).fetchall()
        chapters = []
        for m in mods:
            stats_row = conn.execute(
                """
                SELECT COUNT(s.sprint_id) AS n_sprints,
                       MAX(date(s.start_timestamp)) AS last_read
                FROM SprintSessions s
                WHERE s.agent_id = ? AND s.module_id = ? AND s.end_timestamp IS NOT NULL
                  AND s.completion_status = 'finished_early'
                """,
                (agent_id, m["module_id"]),
            ).fetchone()
            # Quiz stats for this chapter (latest responses)
            qstats = conn.execute(
                """
                SELECT SUM(r.is_correct) AS correct, COUNT(*) AS total,
                       MAX(CAST(lm.score AS FLOAT) / NULLIF(lm.total_questions, 0)) AS last_pct
                FROM QuizResponses r
                JOIN LearningJourney_Map lm ON r.quiz_session_id = lm.quiz_session_id
                JOIN SprintSessions s ON lm.sprint_id = s.sprint_id
                JOIN QuizQuestions q ON r.question_id = q.question_id
                WHERE s.agent_id = ? AND q.module_id = ?
                """,
                (agent_id, m["module_id"]),
            ).fetchone()
            n_sprints = stats_row["n_sprints"] or 0
            total_q = qstats["total"] or 0
            correct_q = qstats["correct"] or 0
            wrong_q = total_q - correct_q
            wrong_rate = (wrong_q / total_q) if total_q else 0
            last_read = stats_row["last_read"]
            days_since = None
            if last_read:
                days_since = (today - datetime.fromisoformat(last_read).date()).days

            if n_sprints == 0:
                score = 20.0
                reason = "尚未讀過，建議先從這章開始"
            else:
                day_factor = min(days_since, 14) / 14.0 if days_since is not None else 0
                score = wrong_rate * 10 * 0.6 + day_factor * 10 * 0.4
                reason = f"距離上次讀 {days_since} 天，答錯率 {round(wrong_rate*100)}%"

            chapters.append({
                "module_id": m["module_id"],
                "title": m["title"],
                "score": round(score, 2),
                "n_sprints": n_sprints,
                "wrong_count": wrong_q,
                "total_answered": total_q,
                "wrong_rate_pct": round(wrong_rate * 100, 1),
                "last_pct": round((qstats["last_pct"] or 0) * 100, 1) if qstats["last_pct"] else None,
                "last_read": last_read,
                "days_since": days_since,
                "reason": reason,
            })

        # Sort desc by score, take top
        chapters.sort(key=lambda c: c["score"], reverse=True)
        top = chapters[0] if chapters else None

        # Overall mastery check — if avg accuracy across all chapters ≥ 90% AND all chapters read,
        # treat as mastered (no urgent recommendation)
        all_read = all(c["n_sprints"] > 0 for c in chapters)
        avg_accuracy = 0
        scored_chs = [c for c in chapters if c["total_answered"] > 0]
        if scored_chs:
            avg_accuracy = sum((c["total_answered"] - c["wrong_count"]) / c["total_answered"]
                               for c in scored_chs) / len(scored_chs) * 100

        return {
            "recommended_chapter": top,
            "all_chapters": chapters,
            "all_read": all_read,
            "avg_accuracy_pct": round(avg_accuracy, 1),
            "mastered": all_read and avg_accuracy >= 90,
            "today": today.isoformat(),
        }


@router.get("/wrong-answers")
def wrong_answers(agent_id: str = "demo-agent-001"):
    """List wrong-answered questions whose LATEST response is still wrong.
    Question correctly answered in a later attempt is excluded.
    """
    with get_conn() as conn:
        # Latest response per question belonging to this agent
        rows = conn.execute(
            """
            SELECT q.question_id, q.module_id, q.sequence_number, q.stem, q.options_json,
                   q.correct_index, q.explanation, q.source_page_seq, m.title AS module_title,
                   r.chosen_index, r.is_correct, r.answered_at
            FROM QuizResponses r
            JOIN QuizQuestions q ON r.question_id = q.question_id
            JOIN MicroModules m ON q.module_id = m.module_id
            JOIN LearningJourney_Map j ON r.quiz_session_id = j.quiz_session_id
            JOIN SprintSessions s ON j.sprint_id = s.sprint_id
            WHERE s.agent_id = ?
              AND r.response_id IN (
                SELECT MAX(response_id) FROM QuizResponses r2
                WHERE r2.question_id = r.question_id
              )
              AND r.is_correct = 0
            ORDER BY r.answered_at DESC
            """,
            (agent_id,),
        ).fetchall()
    items = []
    for r in rows:
        items.append({
            "question_id": r["question_id"],
            "module_id": r["module_id"],
            "module_title": r["module_title"],
            "sequence_number": r["sequence_number"],
            "stem": r["stem"],
            "options": json.loads(r["options_json"]),
            "correct_index": r["correct_index"],
            "chosen_index": r["chosen_index"],
            "explanation": r["explanation"],
            "source_page_seq": r["source_page_seq"],
            "answered_at": r["answered_at"],
        })
    return {"count": len(items), "items": items}
