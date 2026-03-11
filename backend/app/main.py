from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    Path(settings.STATIC_DIR).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="SceneScope API",
    description="AI-powered screenplay pre-visualization tool",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static/images", StaticFiles(directory=settings.STATIC_DIR), name="static")

from app.routes import projects, scenes, export
app.include_router(projects.router, prefix="/api")
app.include_router(scenes.router, prefix="/api")
app.include_router(export.router, prefix="/api")

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
