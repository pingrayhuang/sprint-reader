"""Read-only DB inspector — lets the frontend show actual table contents.

NOT for production. For demo / interview visibility only. Only exposes the
tables we explicitly allowlist below to prevent accidental leakage if more
tables are added later.
"""
from fastapi import APIRouter, HTTPException
from app.db import get_conn

router = APIRouter(prefix="/api/inspect", tags=["inspect"])

# Allowlist — only these tables are exposed to the UI.
ALLOWED_TABLES = {
    "Agents", "MicroModules", "FlashcardPages", "QuizQuestions",
    "SprintSessions", "QuizResponses", "LearningJourney_Map",
    "ChapterMastery", "ReviewEvents",
}


@router.get("/tables")
def list_tables():
    """List each allowed table + its row count + column info."""
    out = []
    with get_conn() as conn:
        for name in sorted(ALLOWED_TABLES):
            try:
                info = conn.execute(f"PRAGMA table_info({name})").fetchall()
                count = conn.execute(f"SELECT COUNT(*) AS c FROM {name}").fetchone()["c"]
            except Exception:
                continue
            out.append({
                "name": name,
                "row_count": count,
                "columns": [
                    {
                        "cid": c["cid"],
                        "name": c["name"],
                        "type": c["type"],
                        "notnull": bool(c["notnull"]),
                        "default": c["dflt_value"],
                        "pk": bool(c["pk"]),
                    } for c in info
                ],
            })
    return {"tables": out}


@router.get("/rows/{table}")
def get_rows(table: str, limit: int = 50):
    if table not in ALLOWED_TABLES:
        raise HTTPException(404, f"Table not accessible: {table}")
    limit = max(1, min(limit, 500))
    with get_conn() as conn:
        info = conn.execute(f"PRAGMA table_info({table})").fetchall()
        cols = [c["name"] for c in info]
        rows = conn.execute(
            f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT ?", (limit,)
        ).fetchall()
    return {
        "table": table,
        "columns": cols,
        "rows": [dict(r) for r in rows],
        "returned": len(rows),
        "limit": limit,
    }
