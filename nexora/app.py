"""Nexora HTTP API and UI server."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from nexora.network import get_status, is_elevated, set_online

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Nexora", docs_url=None, redoc_url=None)
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


class ToggleBody(BaseModel):
    online: bool


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def api_status() -> dict:
    status = get_status()
    return {
        "online": status.online,
        "system": status.system,
        "method": status.method,
        "detail": status.detail,
        "adapters": status.adapters,
        "elevated": is_elevated(),
    }


@app.post("/api/toggle")
def api_toggle(body: ToggleBody) -> dict:
    result = set_online(body.online)
    status = get_status()
    return {
        "ok": result.ok,
        "online": status.online,
        "message": result.message,
        "needs_admin": result.needs_admin,
        "adapters": status.adapters,
        "elevated": is_elevated(),
    }
