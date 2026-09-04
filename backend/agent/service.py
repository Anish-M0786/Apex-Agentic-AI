from __future__ import annotations

from uuid import uuid4

from backend.agent.activity import ActivityEvent, safe_event, activity_store
from backend.agent.executor import execute_plan
from backend.agent.models import AgentRequest, AgentResult
from backend.agent.planner import create_plan
from backend.agent.validator import validate_plan


def preview(request: AgentRequest):
    plan = create_plan(request)
    validate_plan(plan)
    return plan


def run(request: AgentRequest) -> AgentResult:
    plan = preview(request)
    return execute_plan(plan, uuid4().hex, request.document_ids)


def run_with_activity(request: AgentRequest, request_id: str, emit) -> AgentResult:
    """Run a workflow while reporting only safe, externally useful milestones.

    Activity events emitted here must NEVER contain:
      - prompts or prompt fragments
      - model reasoning / chain-of-thought
      - internal argument values
      - file paths or secrets

    Only human-readable execution telemetry is exposed.
    """
    emit(safe_event('thinking', 'running', 'Understanding request'))
    emit(safe_event('planning', 'running', 'Planning task'))

    try:
        plan = preview(request)
    except ValueError as exc:
        emit(safe_event('planning', 'failed', 'Planning failed'))
        emit(safe_event('error', 'failed', str(exc)[:120]))
        raise

    emit(safe_event('planning', 'completed', 'Plan ready'))
    emit(safe_event('plan_created', 'completed', 'Plan created', metadata={'plan': plan.model_dump()}))

    result = execute_plan(plan, request_id, request.document_ids, emit=emit)

    if result.success:
        emit(safe_event('completion', 'completed', 'Completed'))
    else:
        error_messages = [e.message for e in result.errors if e.message]
        summary = error_messages[0][:120] if error_messages else 'One or more steps failed'
        emit(safe_event('error', 'failed', summary))

    return result