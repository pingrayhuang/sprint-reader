"""Quiz Engine (mock P2). Serves questions for a module and records responses.

Flow:
  1. Sprint complete → handoff returns quiz_session_id
  2. Frontend calls GET /api/quiz/{module_id}?n=3 → random sample of stem+options
  3. User answers all → POST /api/quiz/submit-batch
  4. POST /api/quiz/finalize → returns score + wrong answers with explanations
     and updates LearningJourney_Map.score
"""
import json
import random
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import get_conn

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/{module_id}")
def get_quiz(module_id: int, n: int = 3):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT question_id, sequence_number, stem, options_json, source_page_seq "
            "FROM QuizQuestions WHERE module_id = ? ORDER BY sequence_number",
            (module_id,),
        ).fetchall()
    if not rows:
        raise HTTPException(404, f"no quiz questions for module {module_id}")
    pool = list(rows)
    pick_n = min(max(n, 1), len(pool))
    picked = random.sample(pool, pick_n)
    # Preserve sequence order for display
    picked.sort(key=lambda r: r["sequence_number"])
    return {
        "module_id": module_id,
        "questions": [
            {
                "question_id": r["question_id"],
                "sequence_number": r["sequence_number"],
                "stem": r["stem"],
                "options": json.loads(r["options_json"]),
                "source_page_seq": r["source_page_seq"],
            }
            for r in picked
        ],
    }


class SubmitReq(BaseModel):
    quiz_session_id: str
    question_id: int
    chosen_index: int


class BatchAnswer(BaseModel):
    question_id: int
    chosen_index: int


class SubmitBatchReq(BaseModel):
    quiz_session_id: str
    answers: list[BatchAnswer]


@router.post("/submit-batch")
def submit_batch(req: SubmitBatchReq):
    if not req.answers:
        raise HTTPException(400, "no answers provided")
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


@router.post("/submit")
def submit(req: SubmitReq):
    with get_conn() as conn:
        q = conn.execute(
            "SELECT correct_index, explanation, module_id, sequence_number, source_page_seq, options_json "
            "FROM QuizQuestions WHERE question_id = ?",
            (req.question_id,),
        ).fetchone()
        if not q:
            raise HTTPException(404, f"question {req.question_id} not found")
        is_correct = 1 if req.chosen_index == q["correct_index"] else 0
        conn.execute(
            "INSERT INTO QuizResponses (quiz_session_id, question_id, chosen_index, is_correct, answered_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (req.quiz_session_id, req.question_id, req.chosen_index, is_correct, _now_iso()),
        )
    return {
        "question_id": req.question_id,
        "is_correct": bool(is_correct),
        "correct_index": q["correct_index"],
        "explanation": q["explanation"],
        "source_page_seq": q["source_page_seq"],
        "options": json.loads(q["options_json"]),
    }


class FinalizeReq(BaseModel):
    quiz_session_id: str
    sprint_id: str
    module_id: int


@router.post("/finalize")
def finalize(req: FinalizeReq):
    with get_conn() as conn:
        resps = conn.execute(
            "SELECT r.question_id, r.chosen_index, r.is_correct, q.correct_index, q.stem, "
            "q.options_json, q.explanation, q.source_page_seq, q.sequence_number "
            "FROM QuizResponses r JOIN QuizQuestions q ON r.question_id = q.question_id "
            "WHERE r.quiz_session_id = ? ORDER BY q.sequence_number",
            (req.quiz_session_id,),
        ).fetchall()
        # Total = number of questions actually served/answered in THIS session
        # (not all QuizQuestions for the module — those may exceed what the quiz served)
        total_q = len(resps)
        score = sum(r["is_correct"] for r in resps)
        conn.execute(
            "UPDATE LearningJourney_Map SET score = ?, total_questions = ? "
            "WHERE quiz_session_id = ? AND sprint_id = ?",
            (score, total_q, req.quiz_session_id, req.sprint_id),
        )
        sprint = conn.execute(
            "SELECT agent_id, tab_switch_count, completion_status, start_timestamp, end_timestamp "
            "FROM SprintSessions WHERE sprint_id = ?",
            (req.sprint_id,),
        ).fetchone()

    reading_sec = None
    if sprint and sprint["end_timestamp"]:
        reading_sec = round(
            (datetime.fromisoformat(sprint["end_timestamp"]) -
             datetime.fromisoformat(sprint["start_timestamp"])).total_seconds(), 1)

    # Forgetting-curve analytics: update mastery + append event (only for valid sprints)
    if sprint and sprint["completion_status"] == "finished_early" and total_q > 0:
        from app.services import mastery
        score_pct = (score / total_q) * 100
        mastery.update_mastery_after_quiz(
            agent_id=sprint["agent_id"],
            module_id=req.module_id,
            score_pct=score_pct,
            reading_seconds=int(reading_sec) if reading_sec else None,
            tab_switch_count=sprint["tab_switch_count"],
        )
        mastery.record_event(
            agent_id=sprint["agent_id"],
            module_id=req.module_id,
            event_type="quiz_completed",
            sprint_id=req.sprint_id,
            quiz_session_id=req.quiz_session_id,
            score_pct=score_pct,
            reading_seconds=int(reading_sec) if reading_sec else None,
            tab_switch_count=sprint["tab_switch_count"],
            recall_quality=mastery.score_to_quality(score_pct),
        )

    return {
        "quiz_session_id": req.quiz_session_id,
        "sprint_id": req.sprint_id,
        "module_id": req.module_id,
        "score": score,
        "total": total_q,
        "answered": len(resps),
        "tab_switch_count": sprint["tab_switch_count"] if sprint else None,
        "completion_status": sprint["completion_status"] if sprint else None,
        "reading_sec": reading_sec,
        "responses": [
            {
                "question_id": r["question_id"],
                "sequence_number": r["sequence_number"],
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
