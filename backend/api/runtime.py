"""Runtime API endpoints for diagnostics and model management.

Endpoints:
    GET  /api/runtime/models  — list available Ollama models
    GET  /api/runtime/health  — runtime health + model status
    POST /api/runtime/test    — diagnostic generation test
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.runtime import AIRuntime, GenerationRequest, RuntimeMessage
from backend.runtime.metrics import metrics

log = logging.getLogger('apex.api.runtime')
router = APIRouter(prefix='/api/runtime', tags=['runtime'])

# Module-level singleton — ONE runtime for all requests
_runtime: AIRuntime | None = None


def _get_runtime() -> AIRuntime:
    """Return the shared runtime singleton."""
    global _runtime
    if _runtime is None:
        _runtime = AIRuntime()
    return _runtime


# ---- request / response models ------------------------------------------


class TestRequest(BaseModel):
    """Request body for the diagnostic test endpoint."""
    message: str = Field(min_length=1, max_length=4000)


# ---- GET /api/runtime/models --------------------------------------------


@router.get('/models')
def list_models() -> dict:
    """Return available models from the Ollama provider."""
    try:
        rt = _get_runtime()
        model_list = rt.manager.models()
        return {
            'provider': 'Local AI',
            'models': [m.model_dump() for m in model_list],
        }
    except Exception:
        log.exception('Failed to list runtime models')
        raise HTTPException(status_code=503, detail='Runtime provider unavailable.')


# ---- GET /api/runtime/health --------------------------------------------


@router.get('/health')
def runtime_health() -> dict:
    """Return runtime health status, model availability, and metrics."""
    try:
        rt = _get_runtime()
        available = rt.health()
        model_avail = rt.manager.configured_model_available() if available else False
        return {
            'provider': 'Local AI',
            'available': available,
            'configured_model': rt.manager.config.model,
            'model_available': model_avail,
            'metrics': metrics.snapshot(),
        }
    except Exception:
        # Even if Ollama is down, return a structured response
        return {
            'provider': 'Local AI',
            'available': False,
            'configured_model': '',
            'model_available': False,
            'metrics': metrics.snapshot(),
        }


# ---- POST /api/runtime/test --------------------------------------------


@router.post('/test')
def test_generation(request: TestRequest) -> dict:
    """Run a diagnostic generation test.

    This endpoint is for diagnostics only.
    Does not expose hidden prompts or internal stack traces.
    """
    try:
        rt = _get_runtime()
        response = rt.generate(
            GenerationRequest(
                messages=[RuntimeMessage(role='user', content=request.message)],
            ),
        )
        return {
            'success': True,
            'model': response.model,
            'response': response.content,
            'usage': response.usage.model_dump(),
            'duration_ms': response.duration_ms,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail='Runtime generation failed.')
