from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    gemini_api_key: str = ""
    llm_provider: str = "gemini"
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "text-embedding-004"
    database_url: str = "sqlite+aiosqlite:///./data/smartfill.db"
    chroma_persist_dir: str = "./data/chroma"
    upload_dir: str = "./data/uploads"
    output_dir: str = "./data/outputs"
    jobs_dir: str = "./data/jobs"


settings = Settings()
