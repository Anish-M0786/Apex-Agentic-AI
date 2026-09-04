import pytest
from fastapi.testclient import TestClient

from backend.agent.activity import ActivityStore, safe_event
from backend.main import app



def test_activity_store_preserves_order_and_serializes_safely():
    store = ActivityStore()
    store.create('request-1')
    first = safe_event('thinking', 'running', 'Understanding request')
    second = safe_event('planning', 'completed', 'Planning complete')
    store.emit('request-1', first)
    store.emit('request-1', second)
    store.finish('request-1', {'request_id': 'request-1', 'status': 'completed'})

    events = list(store.stream('request-1'))
    assert [event.id for event in events[:-1]] == [first.id, second.id]
    assert events[-1] is None
    assert 'prompt' not in first.model_dump_json().lower()


def test_activity_sse_missing_request_returns_404():
    response = TestClient(app).get('/api/agent/events/missing-request')
    assert response.status_code == 404


def test_streamed_agent_run_emits_completion():
    from backend.core.llm import LLMService
    service = LLMService()
    if not service.health_check() or not service.model_available():
        pytest.skip('Ollama model is not available in this environment.')

    client = TestClient(app)
    started = client.post('/api/agent/run?stream=true', json={'message': 'Create a PDF explaining binary search'})
    assert started.status_code == 200
    request_id = started.json()['request_id']
    assert started.json()['status'] == 'started'

    response = client.get(f'/api/agent/events/{request_id}')
    assert response.status_code == 200
    assert 'event: activity' in response.text
    assert 'event: complete' in response.text
    assert 'Understanding request' in response.text
    assert 'Creating PDF' in response.text
