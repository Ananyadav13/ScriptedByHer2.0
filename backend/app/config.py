from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    database_url: str = "sqlite:///./build_trust.db"
    frontend_origin: str = "http://localhost:3000"

    # App LLM model (per PLAN.md §2) — NOT the dev-chat model.
    # Gemini pivot (14 Jul 2026): gemini-2.5-* retired for new keys; pro tiers 429
    # on this key's quota. gemini-3-flash-preview is the verified working model.
    llm_model: str = "gemini-3-flash-preview"


settings = Settings()
