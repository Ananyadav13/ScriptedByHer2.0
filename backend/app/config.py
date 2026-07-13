from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = "sqlite:///./build_trust.db"
    frontend_origin: str = "http://localhost:3000"

    # App LLM model (per PLAN.md §2) — NOT the dev-chat model.
    llm_model: str = "claude-opus-4-8"


settings = Settings()
