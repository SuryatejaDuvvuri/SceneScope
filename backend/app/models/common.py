from pydantic import BaseModel, Field


class MoodResult(BaseModel):
    """Output of the mood classifier."""

    label: str  # tense | uplifting | somber | action
    confidence: float  # 0.0 - 1.0


class AnalysisResult(BaseModel):
    """Output of the scene analyzer (Groq LLM)."""

    vague_elements: list[str]
    clarifying_questions: list[str]
    visual_summary: str


class ImageResult(BaseModel):
    """Output of the image generator."""

    sketch_url: str  # path like /static/images/{scene_id}_{iteration}.png
    provider: str  # "together" or "openai"


# ── New: Depth Features ──


class ShotSuggestion(BaseModel):
    """A suggested camera shot for a scene."""

    shot_type: str  # e.g., "wide shot", "close-up", "over-the-shoulder"
    angle: str  # e.g., "low angle", "eye level", "high angle", "dutch angle"
    movement: str  # e.g., "static", "dolly in", "pan left", "tracking"
    reasoning: str  # why this shot works for the mood/content


class ShotSuggestions(BaseModel):
    """All shot suggestions for a scene."""

    primary: ShotSuggestion
    alternatives: list[ShotSuggestion] = Field(default_factory=list)


class VisualContext(BaseModel):
    """
    Accumulated visual details from locked scenes.
    Used to maintain consistency across scenes.
    """

    characters: dict[str, str] = Field(
        default_factory=dict,
        description="Character name → locked visual description (e.g., 'SARAH': 'mid-30s, red hair, leather jacket')"
    )
    locations: dict[str, str] = Field(
        default_factory=dict,
        description="Location name → locked visual description (e.g., 'FARMHOUSE': 'two-story, faded yellow paint, wrap porch')"
    )
    props: dict[str, str] = Field(
        default_factory=dict,
        description="Recurring prop → description (e.g., 'LOCKET': 'silver, oval, cracked glass')"
    )
    color_palette: str | None = Field(
        default=None,
        description="Overall color palette from project tone (e.g., 'warm earth tones, golden hour')"
    )


class StructureAnalysis(BaseModel):
    """Full-script structure analysis: pacing, arcs, tonal shifts."""

    scene_moods: list[dict] = Field(
        default_factory=list,
        description="Ordered list of {scene_number, heading, mood, confidence} for all scenes"
    )
    tonal_shifts: list[dict] = Field(
        default_factory=list,
        description="Points where mood changes significantly: {from_scene, to_scene, from_mood, to_mood, magnitude}"
    )
    pacing: str = Field(
        default="",
        description="Overall pacing assessment: 'slow build', 'rapid fire', 'ebb and flow', etc."
    )
    arc_summary: str = Field(
        default="",
        description="One-paragraph summary of the emotional arc of the script"
    )


class SceneShotPlan(BaseModel):
    """Structured scene-to-shot-plan output used for prompt assembly."""

    required_subjects: list[str] = Field(default_factory=list)
    ambient_population_hint: str | None = None
    setting_direction: str = ""
    camera_direction: str = ""
    blocking_direction: str = ""
    lighting_direction: str = ""
    continuity_constraints: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)


class RefinementIntent(BaseModel):
    """Structured parser output for user refinement feedback."""

    preserve_constraints: list[str] = Field(default_factory=list)
    change_requests: list[str] = Field(default_factory=list)
    avoid_changes: list[str] = Field(default_factory=list)
    priority: str = "balanced"
    confidence: float = 0.5
