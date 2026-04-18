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
