import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401
from app.api.router import router
from app.config import settings
from app.services.scheduler import scheduler_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    """예약 매칭 루프를 앱 수명에 묶는다 (설계 2026-09-05)."""
    task = asyncio.create_task(scheduler_loop()) if settings.scheduler_enabled else None
    yield
    if task is not None:
        task.cancel()


app = FastAPI(title="DateDrop Korea API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/health")
def health_check():
    return {"status": "ok"}
