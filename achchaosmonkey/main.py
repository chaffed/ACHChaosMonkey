from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.routers import generation
from .db.base import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="ACH Chaos Monkey", lifespan=lifespan)
    app.include_router(generation.router)
    return app


app = create_app()
