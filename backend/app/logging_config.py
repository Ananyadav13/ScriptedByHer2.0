"""Application logging configuration.

Why this module exists: `docker-compose.yml` mounts a logs directory, and several modules
already call `log.info(...)`. Without an explicit configuration the root logger has no
handler and defaults to WARNING, so every one of those calls went nowhere and the mounted
directory stayed empty — the deployment advertised observability it did not have.

Shape:
  - console handler (stdout), so `docker compose logs` and PaaS log collectors work
  - rotating file handler at `settings.log_dir/app.log`, so the mounted volume is real
  - noisy third-party loggers pinned to WARNING (the SDKs log a line per HTTP request)
  - `configure_logging()` is idempotent — safe under uvicorn `--reload`, which imports
    the app module more than once

Deliberately NOT here: per-request access logging (uvicorn already does it) and DEBUG-level
tracing. The signal worth keeping is moderation decisions — who acted on what listing, and
on what evidence — which is what `log_moderation_event` records.
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from .config import settings

_CONSOLE_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_FILE_FORMAT = "%(asctime)s %(levelname)-7s [%(process)d] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# SDKs that log one line per HTTP call — informative at DEBUG, pure noise at INFO.
_NOISY = ("httpx", "httpcore", "google_genai", "google.genai", "urllib3")

MAX_BYTES = 5 * 1024 * 1024   # 5 MB per file
BACKUP_COUNT = 3              # ~20 MB ceiling total

_configured = False


def configure_logging() -> None:
    """Install console + rotating-file handlers on the root logger. Idempotent."""
    global _configured
    if _configured:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Drop any handler a previous import (or uvicorn's own setup) installed, so repeated
    # calls cannot double every line.
    for h in list(root.handlers):
        root.removeHandler(h)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(_CONSOLE_FORMAT, _DATE_FORMAT))
    root.addHandler(console)

    file_path = _file_handler_path()
    if file_path is not None:
        handler = logging.handlers.RotatingFileHandler(
            file_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf8",
        )
        handler.setFormatter(logging.Formatter(_FILE_FORMAT, _DATE_FORMAT))
        root.addHandler(handler)

    for name in _NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)

    _configured = True


def _file_handler_path() -> Path | None:
    """`log_dir/app.log`, or None when file logging is off or the directory is unusable.

    A read-only or missing volume must not stop the app from booting — console logging
    still works, so we warn and carry on rather than crashing at startup.
    """
    if not settings.log_dir:
        return None
    try:
        directory = Path(settings.log_dir)
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "app.log"
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "file logging disabled — cannot use log_dir %r (%s); console only",
            settings.log_dir, exc,
        )
        return None


def log_startup(app_name: str) -> None:
    """One banner recording the configuration this process actually booted with.

    Deployment questions ("was the key pool loaded?", "did it reseed?") are answerable
    from this line alone. Key COUNT only — never the keys themselves.
    """
    log = logging.getLogger("app.startup")
    log.info("%s starting", app_name)
    log.info("  model=%s  gemini_keys=%d", settings.llm_model, len(settings.gemini_key_list))
    log.info("  database=%s", _redact_db_url(settings.database_url))
    log.info("  seed_reset=%s  cors_origins=%s", settings.seed_reset, settings.cors_origins)
    log.info("  log_level=%s  log_dir=%s", settings.log_level, settings.log_dir or "(console only)")
    if not settings.gemini_key_list:
        log.warning(
            "no Gemini API key configured — deterministic surfaces work, "
            "live agent reasoning traces will fail"
        )


def _redact_db_url(url: str) -> str:
    """Hide credentials in a Postgres/MySQL URL; SQLite paths carry none."""
    if "@" not in url:
        return url
    scheme, _, rest = url.partition("://")
    return f"{scheme}://***@{rest.rpartition('@')[2]}"


def log_moderation_event(actor: str, action: str, target: str, **context) -> None:
    """Record one moderation decision — the audit-relevant events, agent or human.

    `CatalogAction` rows are the durable audit trail; this is the operational view of the
    same events, so a deploy can be understood from its logs without opening the database.
    """
    detail = "  ".join(f"{k}={v}" for k, v in context.items() if v not in (None, ""))
    logging.getLogger("app.moderation").info(
        "%s %s %s%s", actor, action, target, f"  {detail}" if detail else "",
    )
