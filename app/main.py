"""FastAPI entry. Mounts API routes and serves frontend as static files under /ui/."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.db import init_migrations
from app.routes import module, sprint, handoff, quiz, stats, review, inspect

app = FastAPI(title="Sprint Reader", description="7-minute micro-learning with behavioral telemetry.")


@app.on_event("startup")
def run_migrations():
    init_migrations()

app.include_router(module.router)
app.include_router(sprint.router)
app.include_router(handoff.router)
app.include_router(quiz.router)
app.include_router(stats.router)
app.include_router(review.router)
app.include_router(inspect.router)

@app.middleware("http")
async def no_stale_pages(request, call_next):
    # Make browsers re-check pages on every visit, so edits show up without a hard refresh.
    response = await call_next(request)
    if request.url.path.startswith(("/ui", "/sp1")):
        response.headers["Cache-Control"] = "no-cache"
    return response

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


# Standalone SP1 site: same frontend, but site-nav.js shows only the 閱讀加速器 tab.
@app.get("/sp1")
@app.get("/sp1/")
def sp1_root():
    return RedirectResponse(url="/sp1/about.html")

app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")
app.mount("/sp1", StaticFiles(directory=FRONTEND_DIR, html=True), name="sp1")


@app.get("/")
def root():
    return RedirectResponse(url="/ui/")


@app.get("/health")
def health():
    return {"status": "ok"}
