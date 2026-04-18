"""Wrong-answer review challenges.
Lets users pick chapters + desired question count → server samples N of their
latest-wrong questions, returns quiz-shape payload. Uses QuizResponses under
the hood (new quiz_session_id, no sprint association).
"""
import json
import random
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import get_conn

router = APIRouter(prefix="/api/review", tags=["review"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _latest_wrong_for_agent(conn, agent_id: str, chapter_ids: list[int] | None = None):
    """Return question rows where user's latest response is wrong."""
    placeholders = ""
    params: list = [agent_id]
    if chapter_ids:
        placeholders = "AND q.module_id IN (" + ",".join("?" for _ in chapter_ids) + ")"
        params.extend(chapter_ids)
    sql = f"""
        SELECT q.question_id, q.module_id, q.sequence_number, q.stem, q.options_json,
               q.correct_index, q.explanation, q.source_page_seq, m.title AS module_title,
               r.chosen_index AS prev_chosen, r.answered_at
        FROM QuizResponses r
        JOIN QuizQuestions q ON r.question_id = q.question_id
        JOIN MicroModules m ON q.module_id = m.module_id
        JOIN LearningJourney_Map lm ON r.quiz_session_id = lm.quiz_session_id
        JOIN SprintSessions s ON lm.sprint_id = s.sprint_id
        WHERE s.agent_id = ?
          AND r.response_id IN (
            SELECT MAX(response_id) FROM QuizResponses r2 WHERE r2.question_id = r.question_id
          )
          AND r.is_correct = 0
          {placeholders}
        ORDER BY r.answered_at DESC
    """
    return conn.execute(sql, params).fetchall()


@router.get("/available")
def available(agent_id: str = "demo-agent-001"):
    """Count of wrong questions per chapter (for setup page)."""
    with get_conn() as conn:
        rows = _latest_wrong_for_agent(conn, agent_id)
        per_chapter: dict[int, dict] = {}
        for r in rows:
            c = per_chapter.setdefault(r["module_id"], {"module_id": r["module_id"], "title": r["module_title"], "count": 0})
            c["count"] += 1
        all_mods = conn.execute(
            "SELECT module_id, title FROM MicroModules ORDER BY sort_order"
        ).fetchall()
    chapters = []
    for m in all_mods:
        info = per_chapter.get(m["module_id"], {"module_id": m["module_id"], "title": m["title"], "count": 0})
        chapters.append(info)
    return {"total_wrong": sum(c["count"] for c in chapters), "chapters": chapters}


class StartReq(BaseModel):
    agent_id: str = "demo-agent-001"
    chapter_ids: list[int] | None = None  # None = all chapters
    n: int | None = 10  # desired question count; server clamps


@router.post("/start")
def start(req: StartReq):
    with get_conn() as conn:
        rows = _latest_wrong_for_agent(conn, req.agent_id, req.chapter_ids)
        if not rows:
            raise HTTPException(404, "你目前沒有錯題可以複習")
        pool = list(rows)
        n = req.n if req.n and req.n > 0 else 10
        pick = random.sample(pool, min(n, len(pool)))
        quiz_session_id = f"review-{uuid.uuid4()}"
    return {
        "quiz_session_id": quiz_session_id,
        "total_available": len(pool),
        "picked": len(pick),
        "questions": [
            {
                "question_id": r["question_id"],
                "module_id": r["module_id"],
                "module_title": r["module_title"],
                "sequence_number": r["sequence_number"],
                "stem": r["stem"],
                "options": json.loads(r["options_json"]),
                "prev_chosen": r["prev_chosen"],
            }
            for r in pick
        ],
    }


class BatchAnswer(BaseModel):
    question_id: int
    chosen_index: int


class SubmitBatchReq(BaseModel):
    quiz_session_id: str
    answers: list[BatchAnswer]


@router.post("/submit-batch")
def submit_batch(req: SubmitBatchReq):
    with get_conn() as conn:
        for a in req.answers:
            q = conn.execute(
                "SELECT correct_index FROM QuizQuestions WHERE question_id = ?",
                (a.question_id,),
            ).fetchone()
            if not q:
                continue
            is_correct = 1 if a.chosen_index == q["correct_index"] else 0
            conn.execute(
                "INSERT INTO QuizResponses (quiz_session_id, question_id, chosen_index, is_correct, answered_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (req.quiz_session_id, a.question_id, a.chosen_index, is_correct, _now_iso()),
            )
    return {"ok": True, "count": len(req.answers)}


class FinalizeReq(BaseModel):
    quiz_session_id: str


@router.post("/finalize")
def finalize(req: FinalizeReq):
    with get_conn() as conn:
        resps = conn.execute(
            """
            SELECT r.question_id, r.chosen_index, r.is_correct,
                   q.correct_index, q.stem, q.options_json, q.explanation,
                   q.source_page_seq, q.sequence_number, q.module_id,
                   m.title AS module_title
            FROM QuizResponses r
            JOIN QuizQuestions q ON r.question_id = q.question_id
            JOIN MicroModules m ON q.module_id = m.module_id
            WHERE r.quiz_session_id = ?
            ORDER BY r.answered_at
            """,
            (req.quiz_session_id,),
        ).fetchall()
    score = sum(r["is_correct"] for r in resps)
    return {
        "quiz_session_id": req.quiz_session_id,
        "score": score,
        "total": len(resps),
        "responses": [
            {
                "question_id": r["question_id"],
                "sequence_number": r["sequence_number"],
                "module_title": r["module_title"],
                "stem": r["stem"],
                "options": json.loads(r["options_json"]),
                "chosen_index": r["chosen_index"],
                "correct_index": r["correct_index"],
                "is_correct": bool(r["is_correct"]),
                "explanation": r["explanation"],
                "source_page_seq": r["source_page_seq"],
            }
            for r in resps
        ],
    }
