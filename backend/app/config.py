from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/books"
    books_storage_path: str = "./data/books"
    anthropic_api_key: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    frontend_url: str = "http://localhost:3000"


settings = Settings()
