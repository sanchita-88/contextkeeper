from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    groq_api_key: str
    qdrant_url: str
    qdrant_api_key: str
    database_url: str = "sqlite+aiosqlite:///./contextkeeper.db"
    backend_port: int = 8000

    # Groq model names — verified production models
    groq_fast_model: str = "llama-3.1-8b-instant"
    groq_smart_model: str = "llama-3.3-70b-versatile"

    # Embedding model — all-MiniLM-L6-v2 produces exactly 384-dim vectors
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    class Config:
        env_file = ".env"

settings = Settings()
