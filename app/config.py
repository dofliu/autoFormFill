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

    # Phase 3: File watcher & auto-indexing
    watch_dirs: str = ""  # Comma-separated paths to monitor, e.g. "~/Documents/papers,~/Research"
    watch_interval: int = 5  # Seconds between filesystem polls (fallback if OS events unavailable)
    auto_index_collection: str = "auto_indexed"  # ChromaDB collection for auto-indexed files
    supported_extensions: str = ".docx,.pdf,.txt,.md,.pptx,.xlsx"  # File extensions to index

    # Phase 2.5.4: LLM retry
    llm_max_retries: int = 3  # Max retry attempts for transient LLM errors
    llm_timeout: float = 60.0  # Per-call timeout in seconds
    llm_retry_base_delay: float = 1.0  # Base delay for exponential backoff (seconds)

    # Phase 4: Chat
    chat_context_rounds: int = 5  # Number of conversation rounds to keep as LLM context

    # Phase 6.1: Authentication
    auth_enabled: bool = True  # Set to False to disable JWT auth (dev mode)
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"  # Secret for signing JWT tokens
    jwt_algorithm: str = "HS256"  # JWT signing algorithm
    jwt_access_token_expire_hours: int = 24  # Access token lifetime in hours
    jwt_refresh_token_expire_days: int = 7  # Refresh token lifetime in days

    def get_watch_dirs(self) -> list[str]:
        """Parse WATCH_DIRS into a list of resolved absolute paths."""
        if not self.watch_dirs.strip():
            return []
        import os
        dirs = []
        for d in self.watch_dirs.split(","):
            d = d.strip()
            if d:
                dirs.append(os.path.abspath(os.path.expanduser(d)))
        return dirs

    def get_supported_extensions(self) -> set[str]:
        """Parse SUPPORTED_EXTENSIONS into a set."""
        return {ext.strip().lower() for ext in self.supported_extensions.split(",") if ext.strip()}


settings = Settings()
