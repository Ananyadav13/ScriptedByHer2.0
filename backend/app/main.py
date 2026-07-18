from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import catalog, disputes, events, investigations, manager, ops, orders, products
from .seed import create_and_seed_if_empty, reset_and_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.seed_reset:
        reset_and_seed()            # dev: fresh DB every boot
    else:
        create_and_seed_if_empty()  # persistent: keep data across restarts
    yield


app = FastAPI(title="Build Trust API", lifespan=lifespan)

# A wildcard origin and credentialed requests are mutually exclusive per the CORS
# spec — browsers reject the pair. This API is cookie-free, so credentials stay off
# and a wildcard (handy for container/LAN demos) remains valid.
_origins = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(investigations.router)
app.include_router(disputes.router)
app.include_router(events.router)
app.include_router(ops.router)
app.include_router(manager.router)
app.include_router(orders.router)
app.include_router(catalog.router)


@app.get("/health")
def health():
    return {"status": "ok"}
