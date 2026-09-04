from __future__ import annotations

from typing import Any, get_args, get_origin

from backend.agent.models import AgentPlan
from backend.config import get_settings
from backend.core.tools import get_tool
from backend.utils.agent_utils import replace_references


def _acyclic(plan: AgentPlan) -> bool:
  graph = {step.id: set(step.depends_on) for step in plan.steps}
  done: set[str] = set()
  while graph:
    ready = [key for key, dependencies in graph.items() if dependencies <= done]
    if not ready:
      return False
    for key in ready:
      done.add(key)
      graph.pop(key)
  return True


def validate_plan(plan: AgentPlan) -> None:
  maximum = getattr(get_settings(), 'agent_max_steps', 10)
  if not plan.steps or len(plan.steps) > maximum:
    raise ValueError('Plan has invalid step count')

  ids = [step.id for step in plan.steps]
  if len(set(ids)) != len(ids):
    raise ValueError('Duplicate step IDs')

  known = set(ids)
  for step in plan.steps:
    tool = get_tool(step.tool)
    if tool is None:
      raise ValueError(f'Unsupported tool: {step.tool}')
    if any(dependency not in known for dependency in step.depends_on):
      raise ValueError('Missing dependency')

    # Steps that depend on previous steps have arguments containing $step.result
    # references which are resolved at execution time. Validating them against
    # the schema with sample/empty placeholder values would produce false
    # failures for fields with min_length or min_items constraints.
    # We only perform static argument validation for independent (root) steps.
    if not step.depends_on:
      prepared_arguments = replace_references(step.arguments, tool.schema)
      try:
        tool.schema.model_validate(prepared_arguments)
      except Exception as exc:
        raise ValueError(f'Malformed arguments for {step.id}') from exc

  if not _acyclic(plan):
    raise ValueError('Cyclic dependencies')
