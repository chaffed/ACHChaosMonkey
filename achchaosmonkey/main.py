from contextlib import asynccontextmanager

from fastapi import FastAPI
from nicegui import ui

from .api.routers import generation, io, validation
from .db.base import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="ACH Chaos Monkey", lifespan=lifespan)
    app.include_router(generation.router)
    app.include_router(validation.router)
    app.include_router(io.router)

    from .ui.app import register_pages

    register_pages()
    ui.run_with(app, title="ACH Chaos Monkey", storage_secret="achchaosmonkey-dev-secret")

    return app


app = create_app()
