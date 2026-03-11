from pydantic_settings import BaseSettings



class Settings(BaseSettings):
    """App configuration loaded from .env file."""

    GROQ_API_KEY: str = ""
    STABILITY_API_KEY: str = ""
    FAL_KEY: str = ""
    GEMINI_API_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""
    HUGGINGFACE_API_TOKEN: str = ""
    HF_MODEL_ID: str = "your-username/scenescope-mood-classifier"
    DATABASE_PATH: str = "./scenescope.db"
    STATIC_DIR: str = "./static/images"
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
