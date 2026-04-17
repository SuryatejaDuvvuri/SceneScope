from pydantic_settings import BaseSettings



class Settings(BaseSettings):
    """App configuration loaded from .env file."""

    GROQ_API_KEY: str = ""
    STABILITY_API_KEY: str = ""
    FAL_KEY: str = ""
    GEMINI_API_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""
    REPLICATE_MODEL_VERSION: str = ""
    IMAGE_PROVIDER_ORDER: str = "stability,replicate"
    HUGGINGFACE_API_TOKEN: str = ""
    HF_MODEL_ID: str = "your-username/scenescope-mood-classifier"
    DATABASE_PATH: str = "./scenescope.db"
    STATIC_DIR: str = "./static/images"
    AUDIO_DIR: str = "./static/audio"
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Image Generation
    IDEOGRAM_API_KEY: str = ""

    # Audio / TTS
    ELEVENLABS_API_KEY: str = ""

    # OAuth / Auth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    JWT_SECRET_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173"
    BACKEND_PUBLIC_URL: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
