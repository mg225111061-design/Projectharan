"""
webapi/app.py — MR.JEFFREY API. FastAPI over the REAL pillar3 engine.
=====================================================================
Every endpoint returns measured whole-program numbers from the actual engine (carrying hotspot fraction +
Amdahl ceiling, ratio ≤ ceiling, grades from the real ADT, honest DECLINEs). The API key submitted to
/api/key/validate is used only to build the provider request and is NEVER logged, written to disk, or
persisted — it lives only for the duration of the request. Run:  uvicorn webapi.app:app --port 8000
(Named `webapi` — not `server` — so it does not shadow the existing HARAN `server.py` module.)
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os

from webapi import engine_bridge as B

app = FastAPI(title="MR.JEFFREY", version="1.0",
              description="Whole-program verified speedup engine — measured, Amdahl-honest, grade-enforced.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class OptimizeBody(BaseModel):
    code: str
    mode: str = "normal"
    provider: Optional[str] = None
    model: Optional[str] = None
    key: Optional[str] = None          # session-only; used to call the proposer, never logged or stored


class KeyBody(BaseModel):
    provider: str
    key: str
    model: Optional[str] = None


@app.get("/api/health")
def health():
    return {"ok": True, "engine": "pillar3", "real": True}


@app.get("/api/modes")
def get_modes():
    return {"modes": B.modes()}


@app.get("/api/providers")
def get_providers():
    return {"providers": B.providers()}


@app.get("/api/corpus")
def get_corpus():
    return B.corpus()


@app.get("/api/demo")
def get_demo():
    return B.demo()


@app.post("/api/optimize")
def post_optimize(body: OptimizeBody):
    # body.key (if any) is passed to the bridge to call the proposer; never logged or stored here.
    return B.run_optimize(body.code, body.mode, body.provider, body.model, body.key)


@app.post("/api/key/validate")
def post_validate(body: KeyBody):
    # body.key is used only to make the live test call inside the bridge; never logged or stored here.
    return B.validate_key(body.provider, body.key, body.model)


# ── static front end ──────────────────────────────────────────────────────────────────────────────────
# Prefer the built React app (web/dist); fall back to the self-contained HTML studio + landing.
_DIST = os.path.join(_ROOT, "web", "dist")
if os.path.isdir(_DIST):
    app.mount("/app", StaticFiles(directory=_DIST, html=True), name="react")


@app.get("/")
def root():
    dist_index = os.path.join(_DIST, "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)
    # fallback: the self-contained landing (works without the React build)
    landing = os.path.join(_ROOT, "mrjeffrey_landing.html")
    if os.path.exists(landing):
        return FileResponse(landing)
    return JSONResponse({"ok": True, "msg": "MR.JEFFREY API up; no front-end build found. See /api/demo."})


@app.get("/studio")
def studio():
    p = os.path.join(_ROOT, "pillar3_studio.html")
    return FileResponse(p) if os.path.exists(p) else JSONResponse({"error": "studio not found"}, status_code=404)


@app.get("/onefile")
def onefile():
    # the entire app in a single self-contained HTML (real embedded data; upgrades to live /api here)
    p = os.path.join(_ROOT, "mrjeffrey.html")
    return FileResponse(p) if os.path.exists(p) else JSONResponse({"error": "mrjeffrey.html not found"}, status_code=404)
