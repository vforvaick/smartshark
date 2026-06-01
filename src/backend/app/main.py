from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import async_session, create_tables
from app.models import *  # noqa: F401,F403 — ensure all models registered
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.analysis import router as analysis_router
from app.routers.captures import router as captures_router
from app.routers.packets import router as packets_router
from app.routers.conversations import router as conversations_router
from app.routers.capture_index import router as capture_index_router
from app.routers.graph import router as graph_router
from app.routers.evidence import router as evidence_router
from app.routers.evidence_links import router as evidence_links_router
from app.routers.redaction import router as redaction_router
from app.routers.deep_analysis import router as deep_analysis_router
from app.routers.annotations import router as annotations_router
from app.routers.capture_slices import router as capture_slices_router
from app.routers.lifecycle import router as lifecycle_router
from app.routers.scoped_analysis import router as scoped_analysis_router
from app.routers.profiles import router as profiles_router
from app.routers.reports import router as reports_router
from app.routers.export import router as export_router
from app.routers.metrics import router as metrics_router
from app.services.seed import ensure_admin_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await create_tables()
    async with async_session() as db:
        await ensure_admin_exists(db, settings.admin_default_password)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Smartshark", version="0.1.0", lifespan=lifespan)
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(analysis_router)
    app.include_router(captures_router)
    app.include_router(packets_router)
    app.include_router(conversations_router)
    app.include_router(capture_index_router)
    app.include_router(graph_router)
    app.include_router(evidence_router)
    app.include_router(evidence_links_router)
    app.include_router(redaction_router)
    app.include_router(deep_analysis_router)
    app.include_router(annotations_router)
    app.include_router(capture_slices_router)
    app.include_router(lifecycle_router)
    app.include_router(scoped_analysis_router)
    app.include_router(profiles_router)
    app.include_router(reports_router)
    app.include_router(export_router)
    app.include_router(metrics_router)
    return app
