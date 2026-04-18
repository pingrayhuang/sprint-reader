"""Module metadata + flashcard pages (mock P1 MicroModules output)."""
import json
from fastapi import APIRouter, HTTPException
from app.db import get_conn

router = APIRouter(prefix="/api/module", tags=["module"])


@router.get("")
def list_modules():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT module_id, title, description, source_doc, domain_tags, "
            "duration_sec, page_count, quiz_count FROM MicroModules ORDER BY sort_order"
        ).fetchall()
    return {
        "source_doc": rows[0]["source_doc"] if rows else "",
        "modules": [
            {
                "module_id": r["module_id"],
                "title": r["title"],
                "description": r["description"],
                "domain_tags": json.loads(r["domain_tags"]),
                "duration_sec": r["duration_sec"],
                "page_count": r["page_count"],
                "quiz_count": r["quiz_count"],
            }
            for r in rows
        ],
    }


@router.get("/{module_id}")
def get_module(module_id: int):
    with get_conn() as conn:
        mod = conn.execute("SELECT * FROM MicroModules WHERE module_id = ?", (module_id,)).fetchone()
        if not mod:
            raise HTTPException(404, f"module {module_id} not found")
        pages = conn.execute(
            "SELECT page_id, sequence_number, page_content_json FROM FlashcardPages "
            "WHERE module_id = ? ORDER BY sequence_number",
            (module_id,),
        ).fetchall()
    return {
        "module_id": mod["module_id"],
        "title": mod["title"],
        "source_doc": mod["source_doc"],
        "domain_tags": json.loads(mod["domain_tags"]),
        "duration_sec": mod["duration_sec"],
        "page_count": mod["page_count"],
        "quiz_count": mod["quiz_count"],
        "pages": [
            {
                "page_id": p["page_id"],
                "sequence_number": p["sequence_number"],
                **json.loads(p["page_content_json"]),
            }
            for p in pages
        ],
    }
