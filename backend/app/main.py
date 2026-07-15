from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import catalog, disputes, events, investigations, manager, ops, products
from .seed import create_and_seed_if_empty, reset_and_seed

app = FastAPI(title="Build Trust API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(investigations.router)
app.include_router(disputes.router)
app.include_router(events.router)
app.include_router(ops.router)
app.include_router(manager.router)
app.include_router(catalog.router)


@app.on_event("startup")
def _startup():
    if settings.seed_reset:
        reset_and_seed()            # dev: fresh DB every boot
    else:
        create_and_seed_if_empty()  # persistent: keep data across restarts


@app.get("/health")
def health():
    return {"status": "ok"}
