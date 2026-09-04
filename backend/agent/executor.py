from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from backend.agent.context import AgentContext
from backend.agent.models import AgentArtifact, AgentError, AgentPlan, AgentResult
from backend.agent.recovery import retry_allowed
from backend.agent.state import WorkflowState
from backend.agent.validator import validate_plan
from backend.core.executor import ToolExecutor
from backend.utils.agent_utils import artifact_from_output, is_reference, relative_output_path
from backend.agent.activity import ActivityEvent, safe_event

log = logging.getLogger('apex.agent')

ActivityCallback = Callable[[ActivityEvent], None]

TOOL_ACTIVITY_LABELS = {
  'create_pdf': 'Creating PDF',
  'create_excel': 'Creating Excel spreadsheet',
  'create_ppt': 'Creating presentation',
  'create_document': 'Creating document',
  'generate_notes': 'Generating study notes',
  'search_knowledge': 'Searching knowledge base',
  'generate_code': 'Writing code',
  'review_code': 'Reviewing code',
  'generate_document_content': 'Generating content',
  'generate_presentation_content': 'Generating presentation content',
  'generate_spreadsheet_content': 'Generating spreadsheet content',
  'summarize_document': 'Summarizing document',
  'generate_quiz': 'Generating quiz questions',
  'generate_flashcards': 'Generating flashcards',
  'export_study_result': 'Exporting study result',
}


def _tool_label(tool: str) -> str:
  return TOOL_ACTIVITY_LABELS.get(tool, 'Running task')


def _resolve_reference(value: Any, context: AgentContext) -> Any:
  if not is_reference(value):
    return value
  tokens = value[1:].split('.')
  if len(tokens) < 2:
    raise ValueError('Invalid result reference')
  step_id = tokens[0]
  if step_id not in context.results:
    raise ValueError('Invalid result reference')

  current: Any
  section = tokens[1]
  if section == 'result':
    current = context.results[step_id]
  elif section == 'artifact':
    artifact = next((artifact for artifact in reversed(context.artifacts) if artifact.get('step_id') == step_id), None)
    if artifact is None:
      raise ValueError('Invalid artifact reference')
    current = artifact
  else:
    raise ValueError('Invalid reference section')

  for token in tokens[2:]:
    if isinstance(current, dict) and token in current:
      current = current[token]
    else:
      raise ValueError('Invalid result reference')
  return current


def _resolve_arguments(arguments: dict[str, Any], context: AgentContext) -> dict[str, Any]:
  return {key: _resolve_reference(value, context) for key, value in arguments.items()}


def _dependency_status(step_id: str, plan: AgentPlan) -> str | None:
  for step in plan.steps:
    if step.id == step_id:
      return step.status
  return None


def _step_can_run(step, plan: AgentPlan) -> bool:
  return all(_dependency_status(dependency, plan) == 'completed' for dependency in step.depends_on)


def _mark_dependents_skipped(plan: AgentPlan, failed_step_id: str) -> None:
  for step in plan.steps:
    if failed_step_id in step.depends_on and step.status == 'pending':
      step.status = 'skipped'


def _capture_artifacts(result: dict[str, Any], artifacts: list[AgentArtifact]) -> None:
  payload = result.get('result')
  if not isinstance(payload, dict):
    return
  file_path = payload.get('file')
  if not file_path:
    return
  artifacts.append(artifact_from_output(file_path, str(payload.get('type', 'file'))))


def execute_plan(plan: AgentPlan, request_id: str = 'agent-request', document_ids: list[str] | None = None, emit: ActivityCallback | None = None) -> AgentResult:
  validate_plan(plan)
  context = AgentContext(request_id=request_id, document_ids=document_ids or [])
  state = WorkflowState(request_id=request_id, user_request=plan.goal, plan=plan)
  errors: list[AgentError] = []
  artifacts: list[AgentArtifact] = []
  executor = ToolExecutor()

  while True:
    pending_steps = [step for step in plan.steps if step.status == 'pending']
    if not pending_steps:
      break

    runnable = None
    for step in pending_steps:
      if _step_can_run(step, plan):
        runnable = step
        break
      if any(_dependency_status(dependency, plan) in {'failed', 'skipped'} for dependency in step.depends_on):
        step.status = 'skipped'
        _mark_dependents_skipped(plan, step.id)
        state.touch()
    if runnable is None:
      if any(step.status == 'pending' for step in plan.steps):
        raise ValueError('Cyclic or unsatisfied dependencies prevented execution')
      break

    step = runnable
    label = _tool_label(step.tool)
    if emit:
      emit(safe_event('tool_selection', 'completed', f'Selected {label.lower()} tool', tool=step.tool))
    step.status = 'running'
    context.current_step = step.id
    state.current_step = step.id
    state.touch()
    if emit:
      emit(safe_event('step_started', 'running', label, tool=step.tool, step_id=step.id, tool_label=label))

    try:
      resolved_arguments = _resolve_arguments(step.arguments, context)
    except ValueError as exc:
      step.status = 'failed'
      error = AgentError(step_id=step.id, message=str(exc))
      errors.append(error)
      state.errors.append(error)
      _mark_dependents_skipped(plan, step.id)
      state.touch()
      if emit:
        emit(safe_event('tool_execution', 'failed', f'{label} failed', tool=step.tool))
      continue

    attempt = 0
    result: dict[str, Any] = {'success': False, 'error': 'Tool failed'}
    while True:
      log.info('agent request=%s step=%s tool=%s attempt=%s', request_id, step.id, step.tool, attempt)
      result = executor.execute(step.tool, resolved_arguments)
      if result.get('success'):
        break
      if not retry_allowed(attempt, str(result.get('error', 'Tool failed'))):
        break
      attempt += 1

    if not result.get('success'):
      step.status = 'failed'
      error = AgentError(step_id=step.id, message=str(result.get('error', 'Tool failed')))
      errors.append(error)
      state.errors.append(error)
      _mark_dependents_skipped(plan, step.id)
      state.touch()
      if emit:
        emit(safe_event('tool_execution', 'failed', f'{label} failed', tool=step.tool))
      continue

    step.status = 'completed'
    payload = result['result']
    context.results[step.id] = payload
    state.step_results[step.id] = payload
    if isinstance(payload, dict) and payload.get('file'):
      artifact = artifact_from_output(payload['file'], str(payload.get('type', 'file')))
      artifacts.append(artifact)
      context.artifacts.append({'step_id': step.id, **artifact.model_dump()})
      state.artifacts.append({'step_id': step.id, **artifact.model_dump()})
      if emit:
        emit(safe_event('artifact', 'completed', f'Created {artifact.filename}', tool=step.tool, step_id=step.id))
    state.touch()
    if emit:
      result_summary = payload.get('result_summary') if isinstance(payload, dict) else None
      emit(safe_event('step_completed', 'completed', label, tool=step.tool, step_id=step.id, tool_label=label, result_summary=result_summary))

  completed = sum(step.status == 'completed' for step in plan.steps)
  skipped = sum(step.status == 'skipped' for step in plan.steps)
  failed = sum(step.status == 'failed' for step in plan.steps)
  status = 'completed' if failed == 0 and skipped == 0 else 'partial_failure' if completed else 'failed'
  return AgentResult(
    success=failed == 0 and skipped == 0,
    request_id=request_id,
    status=status,
    summary=f'Executed {completed} of {len(plan.steps)} steps.',
    steps=plan.steps,
    artifacts=artifacts,
    errors=errors,
  )
