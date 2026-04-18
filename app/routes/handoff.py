"""Handoff to mock Quiz Engine (P2). Generates quiz_session_id and writes LearningJourney_Map."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import get_conn
from app.services import session_manager

router = APIRouter(prefix="/api/handoff", tags=["handoff"])


class HandoffReq(BaseModel):
    sprint_id: str


@router.post("/to-quiz")
def to_quiz(req: HandoffReq):
    sprint = session_manager.get_sprint(req.sprint_id)
    if not sprint:
        raise HTTPException(404, f"sprint {req.sprint_id} not found")
    if sprint["completion_status"] == "in_progress":
        raise HTTPException(400, "sprint not yet completed; call /api/sprint/complete first")

    quiz_session_id = f"quiz-{uuid.uuid4()}"
    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO LearningJourney_Map (sprint_id, quiz_session_id, created_at) VALUES (?, ?, ?)",
            (req.sprint_id, quiz_session_id, created),
        )
    return {
        "sprint_id": req.sprint_id,
        "quiz_session_id": quiz_session_id,
        "module_id": sprint["module_id"],
        "tab_switch_count": sprint["tab_switch_count"],
        "completion_status": sprint["completion_status"],
        "created_at": created,
        "next": f"/ui/handoff.html?sprint_id={req.sprint_id}&quiz_session_id={quiz_session_id}",
    }
