from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentContext(BaseModel):
	request_id: str
	document_ids: list[str] = Field(default_factory=list)
	results: dict[str, Any] = Field(default_factory=dict)
	artifacts: list[dict[str, Any]] = Field(default_factory=list)
	current_step: str | None = None
