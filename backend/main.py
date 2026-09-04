"""Apex FastAPI application entry point."""

from __future__ import annotations

import os
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.api.agent import router as agent_router
from backend.api.chat import router as chat_router
from backend.api.code import router as code_router
from backend.api.documents import router as documents_router
from backend.api.files import router as files_router
from backend.api.intelligence import router as intelligence_router
from backend.api.runtime import router as runtime_router
from backend.api.voice import router as voice_router
from backend.config import get_settings
from backend.core.llm import LLMService
from backend.utils.logger import configure_logging, logger

configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Try to start Ollama if it's not running
    settings = get_settings()
    service = LLMService(settings)
    if not service.health_check():
        logger.info("Ollama is not running. Attempting to start 'ollama serve' in the background...")
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
        except Exception as e:
            logger.warning("Failed to automatically start Ollama: %s", e)
    yield

app = FastAPI(title="Apex API", description="Local-first AI productivity platform.", lifespan=lifespan)

# ---- CORS -----------------------------------------------------------------
# Restrict to the configured frontend origin — never use wildcard in production.
_allowed_origins = [os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# ---- Routers ---------------------------------------------------------------
app.include_router(chat_router)
app.include_router(files_router)
app.include_router(intelligence_router)
app.include_router(code_router)
app.include_router(agent_router)
app.include_router(runtime_router)
app.include_router(documents_router)
app.include_router(voice_router)


# ---- Middleware ------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("Incoming %s %s", request.method, request.url.path)
    return await call_next(request)


# ---- Root ------------------------------------------------------------------
@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Apex", "status": "running"}


# ---- Health ----------------------------------------------------------------
@app.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    service = LLMService(settings)
    ok = service.health_check()
    model_ok = service.model_available() if ok else False
    return {
        "status": "healthy" if ok and model_ok else "degraded",
        "ollama": ok,
        "model": settings.ollama_model,
        "model_available": model_ok,
    }
