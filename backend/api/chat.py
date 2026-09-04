"""Chat API — routes user messages to the correct handler.

Routing logic (in priority order):
  1. workflow   → Agent Engine (multi-step, planner, SSE)
  2. rag_chat   → RAG retrieval from uploaded documents + Qwen
  3. single_tool → ToolExecutor (single file creation or code op)
  4. simple_chat → Direct LLMService call (plain conversation)

document_ids are forwarded from the frontend when the user has uploaded PDFs.
The router decides whether those IDs are relevant based on message intent.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.agent.models import AgentRequest
from backend.agent.service import run
from backend.config import get_settings
from backend.core.executor import ToolExecutor
from backend.core.llm import LLMService
from backend.core.memory import context as memory_context, learn_from_message, save_feedback
from backend.core.rag import rag_chat
from backend.core.router import decide
from backend.core.security import sanitize_input

log = logging.getLogger("apex.api.chat")
router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    document_ids: list[str] = Field(default_factory=list)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=8)


class FeedbackRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    response: str = Field(min_length=1, max_length=8000)
    rating: str = Field(pattern='^(positive|negative)$')
    comment: str = Field(default='', max_length=1000)


class ChatResponse(BaseModel):
    response: str
    model: str
    success: bool


@router.post("/api/feedback")
def feedback(request: FeedbackRequest):
    save_feedback(request.message, request.response, request.rating, request.comment)
    return {"success": True}


@router.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        sanitize_input(request.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    settings = get_settings()
    decision = decide(request.message, document_ids=request.document_ids or None)

    # ---- 1. Multi-step agent workflow --------------------------------------
    if decision.intent == "workflow":
        try:
            result = run(AgentRequest(message=request.message, document_ids=request.document_ids))
            return ChatResponse(
                response=result.summary or "Workflow completed.",
                model=settings.ollama_model,
                success=result.success,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            log.exception("Agent workflow failed: %s", exc)
            raise HTTPException(status_code=503, detail="Agent workflow failed.") from exc

    # ---- 2. RAG-grounded document chat ------------------------------------
    if decision.intent == "rag_chat":
        try:
            response_text = rag_chat(request.message, request.document_ids, request.history)
            return ChatResponse(
                response=response_text,
                model=settings.ollama_model,
                success=True,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            log.exception("RAG chat failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Unable to retrieve document content. Check the document ID.",
            ) from exc

    # ---- 3. Single registered tool ----------------------------------------
    if decision.intent == "single_tool" and decision.tool:
        result = ToolExecutor().execute(decision.tool, decision.arguments)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return ChatResponse(
            response=f"Completed {decision.tool}",
            model=settings.ollama_model,
            success=True,
        )

    # ---- 4. Plain LLM conversation ----------------------------------------
    try:
        system_prompt = (
            "You are Apex, a warm Indian English AI assistant. "
            "Enforce natural conversational phrasing (e.g. 'Sure, I'll create that for you') and very light contextual slang, while keeping it professional for tasks. "
            "Recognize emotional intent, validate the user briefly, match their tone, and be genuinely helpful. "
            "Do not claim to have human feelings or encourage dependency. "
            "Respect the user's autonomy, including if they want to uninstall or stop using Apex. "
            "Use local memory only when relevant: " + (memory_context() or "No saved preferences yet.")
        )
        return ChatResponse(
            response=LLMService(settings).chat([{"role": "system", "content": system_prompt}] + request.history[-8:] + [{"role": "user", "content": request.message}]),
            model=settings.ollama_model,
            success=True,
        )
    except Exception as exc:
        log.exception("Chat request failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Unable to reach or use the configured AI model.",
        ) from exc
