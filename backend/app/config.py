from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/books"
    books_storage_path: str = "./data/books"
    anthropic_api_key: str = ""
    aws_bearer_token_bedrock: str = ""
    aws_bedrock_region: str = "us-east-1"
    bedrock_model: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_cache_path: str | None = None
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    frontend_url: str = "http://localhost:3000"


settings = Settings()
