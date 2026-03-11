from pydantic import BaseModel, Field
from datetime import datetime


# ── Request Models ──


class ProjectCreate(BaseModel):
    title: str
    genre: str | None = None
    time_period: str | None = None
    tone: str | None = None
    films: list[str] = Field(default_factory=list)


# ── Response Models ──


class ProjectSummary(BaseModel):
    """Lightweight project info for list views."""

    id: str
    title: str
    genre: str | None
    scene_count: int = 0
    created_at: str


class ProjectResponse(BaseModel):
    """Full project detail with scenes."""

    id: str
    title: str
    genre: str | None
    time_period: str | None
    tone: str | None
    films: list[str]
    scenes: list = Field(default_factory=list)  # list[SceneResponse] — avoids circular import
    created_at: str
    updated_at: str
