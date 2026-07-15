from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""            # single key (back-compat)
    gemini_api_keys: str = ""           # optional comma-separated POOL for daily-cap failover
    database_url: str = "sqlite:///./build_trust.db"
    frontend_origin: str = "http://localhost:3000"

    # Dev drops + reseeds on every boot. Set False in a persistent deployment
    # (docker volume / prod) so data, logs and history survive restarts.
    seed_reset: bool = True

    # App LLM model (per PLAN.md §2) — NOT the dev-chat model.
    # Gemini pivot (14 Jul 2026): gemini-2.5-* retired for new keys; pro tiers 429
    # on this key's quota. gemini-3-flash-preview is the verified working model.
    llm_model: str = "gemini-3-flash-preview"

    @property
    def gemini_key_list(self) -> list[str]:
        """All usable keys, in order. The pool (GEMINI_API_KEYS) takes precedence;
        falls back to the single GEMINI_API_KEY. De-duplicated, order preserved."""
        raw = self.gemini_api_keys or self.gemini_api_key
        seen: dict[str, None] = {}
        for k in raw.split(","):
            k = k.strip()
            if k:
                seen.setdefault(k, None)
        return list(seen)


settings = Settings()
