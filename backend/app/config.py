from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

# Directory containing requirements.txt / static/ — always correct regardless of cwd.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """App configuration loaded from .env file."""

    GROQ_API_KEY: str = ""
    STABILITY_API_KEY: str = ""
    FAL_KEY: str = ""
    GEMINI_API_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""
    REPLICATE_MODEL_VERSION: str = ""
    IMAGE_PROVIDER_ORDER: str = "gemini,fal,ideogram,stability,replicate"
    HUGGINGFACE_API_TOKEN: str = ""
    HF_MODEL_ID: str = "your-username/scenescope-mood-classifier"
    HF_INFERENCE_ENDPOINT_URL: str = ""
    DATABASE_PATH: str = "./scenescope.db"
    STATIC_DIR: str = "./static/images"
    AUDIO_DIR: str = "./static/audio"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Image Generation
    IDEOGRAM_API_KEY: str = ""

    # Audio / TTS
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_FALLBACK_VOICE_ID: str = ""

    # OAuth / Auth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    JWT_SECRET_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173"
    BACKEND_PUBLIC_URL: str = ""

    # Product limits / abuse guardrails
    MAX_PROJECTS_PER_USER: int = 1
    MAX_SCENES_PER_PROJECT: int = 3
    MAX_SCENES_PER_UPLOAD: int = 3
    MAX_IMAGE_GENERATIONS_PER_DAY: int = 120

    # Consistency behavior
    STRICT_REFERENCE_REFINEMENT: bool = True

    # Director agent tuning
    DIRECTOR_TEMPERATURE: float = 0.35

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @model_validator(mode="after")
    def resolve_paths_relative_to_backend(self):
        """Render (and some shells) start uvicorn with cwd = repo root, not ``backend/``.

        Relative ``DATABASE_PATH`` / ``STATIC_DIR`` / ``AUDIO_DIR`` would then
        point at the wrong place and ``StaticFiles`` fails before lifespan runs.
        """
        for field in ("DATABASE_PATH", "STATIC_DIR", "AUDIO_DIR"):
            raw = getattr(self, field)
            p = Path(raw)
            if not p.is_absolute():
                setattr(self, field, str((_BACKEND_ROOT / p).resolve()))
        return self


settings = Settings()
