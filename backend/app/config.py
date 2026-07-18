from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""            # single key (back-compat)
    gemini_api_keys: str = ""           # optional comma-separated POOL for daily-cap failover
    database_url: str = "sqlite:///./build_trust.db"
    # Comma-separated list of browser origins allowed to call this API.
    frontend_origin: str = "http://localhost:3000"

    # Dev drops + reseeds on every boot. Set False in a persistent deployment
    # (docker volume / prod) so data, logs and history survive restarts.
    seed_reset: bool = True

    # gemini-2.5-* is retired for new keys and the pro tiers 429 on the free quota;
    # gemini-3-flash-preview is the verified working model for this project.
    llm_model: str = "gemini-3-flash-preview"

    @property
    def cors_origins(self) -> list[str]:
        """Allowed browser origins. `*` is returned as a single wildcard entry —
        `main.py` then disables credentialed CORS, since browsers reject the
        wildcard-plus-credentials combination outright."""
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]

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
