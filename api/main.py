from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes.health import router as health_router
from api.routes.ingest import router as ingest_router
from api.routes.incidents import router as incidents_router
from api.routes.metrics import router as metrics_router

UI_DIR = Path(__file__).resolve().parent.parent / "ui"

app = FastAPI(title="Causeway", version="0.1.0")
app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(incidents_router)
app.include_router(metrics_router)

if UI_DIR.is_dir():
    app.mount("/ui/static", StaticFiles(directory=UI_DIR), name="ui-static")

    @app.get("/ui")
    @app.get("/ui/")
    async def ui_home() -> FileResponse:
        return FileResponse(UI_DIR / "index.html")

    @app.get("/")
    async def root_redirect() -> FileResponse:
        return FileResponse(UI_DIR / "index.html")
