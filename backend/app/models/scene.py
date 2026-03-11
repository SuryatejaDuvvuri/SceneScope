from pydantic import BaseModel, Field
from app.models.common import ShotSuggestions


# ── Request Models ──


class ScenesCreate(BaseModel):
    """Raw screenplay text to be parsed into scenes."""

    text: str


class RefineRequest(BaseModel):
    """User's answers to clarifying questions + optional freeform feedback."""

    answers: dict[str, str] = Field(default_factory=dict)
    feedback: str | None = None
    director_notes: dict | None = Field(
        default=None,
        description="Confirmed Director Agent notes from /consult flow. If provided, skips re-consulting."
    )


# ── Response Models ──


class DirectorNotes(BaseModel):
    """Director Agent's interpretation and reasoning for a refinement."""

    interpretation: str = ""
    visual_direction: str = ""
    reasoning: str = ""
    prompt_modifier: str = ""
    follow_up: str | None = None


class ConsultRequest(BaseModel):
    """Initial feedback to the Director Agent."""

    feedback: str
    answers: dict[str, str] = Field(default_factory=dict)


class ConsultFollowUpRequest(BaseModel):
    """User's response to the Director's follow-up question."""

    response: str
    conversation_history: list[dict] = Field(default_factory=list)


class ConsultResponse(BaseModel):
    """Director Agent's interpretation + optional follow-up question."""

    interpretation: str
    visual_direction: str
    reasoning: str
    prompt_modifier: str
    follow_up: str | None = None


class SceneIterationResponse(BaseModel):
    id: str
    iteration_number: int
    prompt_used: str
    answers: dict[str, str] | None
    feedback: str | None
    sketch_url: str | None
    image_provider: str | None
    director_notes: DirectorNotes | None = None
    created_at: str


class SceneResponse(BaseModel):
    id: str
    project_id: str
    scene_number: int
    heading: str | None
    description: str
    mood: str | None
    mood_confidence: float | None
    vague_elements: list[str]
    clarifying_questions: list[dict | str]
    visual_summary: str | None
    shot_suggestions: ShotSuggestions | None = None
    current_iteration: SceneIterationResponse | None = None
    iterations: list[SceneIterationResponse] = Field(default_factory=list)
    locked: bool = False
    created_at: str
    updated_at: str


class ScenesCreateResponse(BaseModel):
    """Response after parsing + analyzing a screenplay."""

    scenes: list[SceneResponse]
