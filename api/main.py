from fastapi import FastAPI



from api.routes.health import router as health_router
from api.routes.ingest import router as ingest_router
from api.routes.incidents import router as incidents_router

app = FastAPI(title="Causeway", version="0.1.0")
app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(incidents_router)