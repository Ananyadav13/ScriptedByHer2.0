from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import products
from .seed import reset_and_seed

app = FastAPI(title="Build Trust API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)


@app.on_event("startup")
def _startup():
    reset_and_seed()  # idempotent dev seed


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/smoke")
def smoke():
    """Phase-1 only: proves GEMINI_API_KEY + function-calling loop work. Remove in Phase 2."""
    from .agents.orchestrator import smoke_test
    try:
        return {"ok": True, "response": smoke_test()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
