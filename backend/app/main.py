from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app import models  # noqa: F401 - registers every mapped table before create_all
from app.routers import auth, catalog, deposits, operations, points, users


@asynccontextmanager
async def lifespan(application: FastAPI):
    active_engine = application.state.engine
    Base.metadata.create_all(bind=active_engine)
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="EcoPunto API",
        description="API inicial de gestión para la plataforma EcoPunto Autónomo.",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.engine = engine
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Bootstrap-Token"],
    )
    prefix = "/api/v1"
    for route in (auth.router, users.router, catalog.router, deposits.router, points.router, operations.router):
        application.include_router(route, prefix=prefix)

    @application.get("/health", tags=["Sistema"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
