"""Pydantic models for the Apex AI Runtime."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class RuntimeMessage(BaseModel):
    """A single message in a conversation."""

    role: str
    content: str = Field(min_length=1)

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ('system', 'user', 'assistant'):
            raise ValueError(f"Role must be 'system', 'user', or 'assistant', got '{v}'")
        return v


class GenerationRequest(BaseModel):
    """Request to generate a completion."""

    model: str | None = None
    messages: list[RuntimeMessage] = Field(min_length=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=4096)
    stream: bool = False


class StructuredGenerationRequest(GenerationRequest):
    """Generation request expecting structured JSON output."""

    response_schema: dict[str, Any] = Field(
        default_factory=dict,
        description='JSON schema the model output must conform to.',
    )


class Usage(BaseModel):
    """Token usage statistics from a generation."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class GenerationResponse(BaseModel):
    """Structured response from the AI runtime."""

    success: bool
    model: str
    content: str
    usage: Usage
    duration_ms: int
    request_id: str


class ModelInfo(BaseModel):
    """Metadata about an available model."""

    name: str
    size: int | None = None
