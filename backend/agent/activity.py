"""Safe, user-facing activity events for agent workflows.

This module deliberately contains no model prompts, reasoning, tool arguments, or
filesystem paths.  It is the sole event shape exposed to clients.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Condition, Lock
from typing import Any, Iterator, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ActivityType = Literal[
    'thinking', 'planning', 'plan_created', 'step_started', 'step_completed', 'step_added', 'tool_selection', 'tool_execution', 'retrieval',
    'generation', 'artifact', 'completion', 'error'
]
ActivityStatus = Literal['pending', 'running', 'completed', 'failed', 'skipped']


class ActivityEvent(BaseModel):
    id: str = Field(default_factory=lambda: f'evt_{uuid4().hex}')
    type: ActivityType
    status: ActivityStatus
    label: str = Field(min_length=1, max_length=200)
    tool: str | None = Field(default=None, max_length=80)
    step_id: str | None = Field(default=None)
    result_summary: str | None = Field(default=None)
    tool_label: str | None = Field(default=None)
    narration: str | None = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActivityStore:
    """Small in-memory event broker; event order is append order per request."""
    def __init__(self, max_requests: int = 200) -> None:
        self._requests: dict[str, dict[str, Any]] = {}
        self._order: deque[str] = deque(maxlen=max_requests)
        self._lock = Lock()

    def create(self, request_id: str) -> None:
        with self._lock:
            if request_id not in self._requests:
                if len(self._order) == self._order.maxlen:
                    expired = self._order.popleft()
                    self._requests.pop(expired, None)
                self._order.append(request_id)
                self._requests[request_id] = {'events': [], 'done': False, 'result': None, 'condition': Condition(self._lock)}

    def emit(self, request_id: str, event: ActivityEvent) -> None:
        with self._lock:
            record = self._requests.get(request_id)
            if record is None:
                return
            record['events'].append(event)
            record['condition'].notify_all()

    def finish(self, request_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            record = self._requests.get(request_id)
            if record is None:
                return
            record['done'] = True
            record['result'] = result
            record['condition'].notify_all()

    def exists(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._requests

    def stream(self, request_id: str) -> Iterator[ActivityEvent | None]:
        """Yield events in append order, then ``None`` when the workflow ends."""
        index = 0
        while True:
            with self._lock:
                record = self._requests.get(request_id)
                if record is None:
                    return
                while index >= len(record['events']) and not record['done']:
                    record['condition'].wait(timeout=15)
                if index < len(record['events']):
                    event = record['events'][index]
                    index += 1
                elif record['done']:
                    event = None
                else:
                    continue
            yield event
            if event is None:
                return

    def result(self, request_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._requests.get(request_id)
            return None if record is None else record['result']


activity_store = ActivityStore()


def safe_event(event_type: ActivityType, status: ActivityStatus, label: str, *, tool: str | None = None, step_id: str | None = None, result_summary: str | None = None, tool_label: str | None = None, metadata: dict[str, Any] | None = None) -> ActivityEvent:
    return ActivityEvent(type=event_type, status=status, label=label, tool=tool, step_id=step_id, result_summary=result_summary, tool_label=tool_label, metadata=metadata or {})
