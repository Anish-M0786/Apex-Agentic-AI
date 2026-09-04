from __future__ import annotations

import json
from threading import Thread
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.agent.activity import activity_store, safe_event
from backend.agent.models import AgentRequest
from backend.agent.service import preview, run, run_with_activity

router = APIRouter(prefix='/api/agent', tags=['agent'])


@router.post('/plan')
def plan(request: AgentRequest):
    try:
        return {'valid': True, 'plan': preview(request).model_dump()}
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception:
        raise HTTPException(503, 'Unable to create agent plan.')


@router.post('/run')
def agent_run(request: AgentRequest, stream: bool = False):
    """Start an event-streamed workflow when ``stream=true``.

    The synchronous default remains for existing API consumers; new chat clients
    use ``?stream=true`` and subscribe with the returned request id.
    """
    if not stream:
        try:
            return run(request).model_dump()
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        except Exception:
            raise HTTPException(503, 'Agent workflow failed.')

    request_id = uuid4().hex
    activity_store.create(request_id)

    def worker() -> None:
        try:
            result = run_with_activity(request, request_id, lambda event: activity_store.emit(request_id, event))
            activity_store.finish(request_id, result.model_dump(mode='json'))
        except ValueError:
            activity_store.emit(request_id, safe_event('error', 'failed', 'Unable to plan workflow'))
            activity_store.finish(request_id, {'request_id': request_id, 'status': 'failed'})
        except Exception:
            # The client receives a safe message, never exception details.
            activity_store.emit(request_id, safe_event('error', 'failed', 'Agent workflow failed'))
            activity_store.finish(request_id, {'request_id': request_id, 'status': 'failed'})

    Thread(target=worker, name=f'apex-agent-{request_id[:8]}', daemon=True).start()
    return {'request_id': request_id, 'status': 'started'}


@router.get('/events/{request_id}')
def agent_events(request_id: str):
    if not activity_store.exists(request_id):
        raise HTTPException(404, 'Unknown agent request.')

    def event_stream():
        for event in activity_store.stream(request_id):
            if event is None:
                result = activity_store.result(request_id) or {'request_id': request_id, 'status': 'completed'}
                yield f'event: complete\ndata: {json.dumps(result, separators=(",", ":"))}\n\n'
                return
            yield f'event: activity\ndata: {event.model_dump_json()}\n\n'

    return StreamingResponse(
        event_stream(), media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no'},
    )