from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import events, investigations, products
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
app.include_router(investigations.router)
app.include_router(events.router)


@app.on_event("startup")
def _startup():
    reset_and_seed()  # idempotent dev seed


@app.get("/health")
def health():
    return {"status": "ok"}
