from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

StepStatus = Literal['pending', 'running', 'completed', 'failed', 'skipped']


class AgentRequest(BaseModel):
	message: str = Field(min_length=1, max_length=12000)
	document_ids: list[str] = Field(default_factory=list, max_length=10)


class AgentStep(BaseModel):
	id: str = Field(min_length=1, max_length=64)
	title: str = Field(default="", max_length=200)
	tool: str
	arguments: dict[str, Any] = Field(default_factory=dict)
	depends_on: list[str] = Field(default_factory=list)
	status: StepStatus = 'pending'


class AgentPlan(BaseModel):
	goal: str
	steps: list[AgentStep] = Field(default_factory=list)


class AgentArtifact(BaseModel):
	filename: str
	type: str
	path: str
	download_url: str


class AgentError(BaseModel):
	step_id: str | None = None
	message: str


class AgentResult(BaseModel):
	success: bool
	request_id: str
	status: str
	summary: str
	steps: list[AgentStep]
	artifacts: list[AgentArtifact] = Field(default_factory=list)
	errors: list[AgentError] = Field(default_factory=list)
