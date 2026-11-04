"""Sprint session endpoints. State transitions live in services/session_manager.py."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services import session_manager

router = APIRouter(prefix="/api/sprint", tags=["sprint"])


class StartReq(BaseModel):
    agent_id: str = Field(..., min_length=1)
    module_id: int


class TelemetryReq(BaseModel):
    sprint_id: str
    event: str  # currently only "tab_switch"


class CompleteReq(BaseModel):
    sprint_id: str
    status: str  # finished_early | timed_out | abandoned


class ConfidenceReq(BaseModel):
    sprint_id: str
    page_id: int
    confidence: int = Field(..., ge=1, le=3)  # 1=不確定 2=還好 3=有把握


@router.post("/start")
def start(req: StartReq):
    return session_manager.start_sprint(req.agent_id, req.module_id)


@router.post("/telemetry")
def telemetry(req: TelemetryReq):
    if req.event != "tab_switch":
        raise HTTPException(400, f"unsupported event: {req.event}")
    try:
        count = session_manager.increment_tab_switch(req.sprint_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"sprint_id": req.sprint_id, "tab_switch_count": count}


@router.post("/complete")
def complete(req: CompleteReq):
    try:
        return session_manager.complete_sprint(req.sprint_id, req.status)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/confidence")
def confidence(req: ConfidenceReq):
    from app.db import get_conn
    from datetime import datetime, timezone
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO CardConfidenceRatings "
            "(sprint_id, page_id, confidence, rated_at) VALUES (?, ?, ?, ?)",
            (req.sprint_id, req.page_id, req.confidence,
             datetime.now(timezone.utc).isoformat()),
        )
    return {"ok": True}


@router.get("/{sprint_id}/stats")
def sprint_stats(sprint_id: str):
    from app.db import get_conn
    from datetime import datetime
    with get_conn() as conn:
        row = conn.execute(
            "SELECT tab_switch_count, completion_status, start_timestamp, end_timestamp "
            "FROM SprintSessions WHERE sprint_id = ?",
            (sprint_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, f"sprint {sprint_id} not found")
    reading_sec = None
    if row["end_timestamp"] and row["start_timestamp"]:
        reading_sec = round(
            (datetime.fromisoformat(row["end_timestamp"]) -
             datetime.fromisoformat(row["start_timestamp"])).total_seconds(), 1)
    return {
        "sprint_id": sprint_id,
        "tab_switch_count": row["tab_switch_count"],
        "completion_status": row["completion_status"],
        "reading_sec": reading_sec,
    }
