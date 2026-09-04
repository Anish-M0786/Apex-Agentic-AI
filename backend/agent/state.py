from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from backend.agent.models import AgentError, AgentPlan


class WorkflowState(BaseModel):
	request_id: str
	user_request: str
	plan: AgentPlan
	status: str = 'pending'
	current_step: str | None = None
	step_results: dict[str, Any] = Field(default_factory=dict)
	artifacts: list[dict[str, Any]] = Field(default_factory=list)
	errors: list[AgentError] = Field(default_factory=list)
	created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
	updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

	def touch(self) -> None:
		self.updated_at = datetime.now(timezone.utc).isoformat()
