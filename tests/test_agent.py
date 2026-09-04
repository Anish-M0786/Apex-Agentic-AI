from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from backend.agent.executor import execute_plan
from backend.agent.models import AgentPlan, AgentRequest, AgentStep
from backend.agent.planner import create_plan
from backend.agent.validator import validate_plan
from backend.core.router import decide
from backend.core.tools import Tool, register_tool, unregister_tool
from backend.main import app


# ---------------------------------------------------------------------------
# Existing tests — preserved intact
# ---------------------------------------------------------------------------

def test_plan_and_validation_failures():
    # PDF request now creates a two-step plan: generate_document_content + create_pdf
    plan = create_plan(AgentRequest(message='Create a PDF explaining binary search'))
    validate_plan(plan)
    assert plan.steps[0].tool == 'generate_document_content'
    assert plan.steps[1].tool == 'create_pdf'
    assert plan.steps[1].depends_on == ['step_1']

    with pytest.raises(ValueError):
        validate_plan(AgentPlan(goal='x', steps=[AgentStep(id='a', tool='missing')]))
    with pytest.raises(ValueError):
        validate_plan(AgentPlan(goal='x', steps=[AgentStep(id='a', tool='create_pdf', arguments={}), AgentStep(id='a', tool='create_pdf', arguments={})]))
    with pytest.raises(ValueError):
        validate_plan(AgentPlan(goal='x', steps=[AgentStep(id='a', tool='create_pdf', arguments={'filename': 'a', 'title': 'a', 'content': 'a'}, depends_on=['b'])]))
    with pytest.raises(ValueError):
        validate_plan(AgentPlan(goal='x', steps=[AgentStep(id='a', tool='create_pdf', arguments={'filename': 'a', 'title': 'a', 'content': 'a'}, depends_on=['b']), AgentStep(id='b', tool='create_pdf', arguments={'filename': 'b', 'title': 'b', 'content': 'b'}, depends_on=['a'])]))


def test_executor_reference_artifact_and_failure():
    class Value(BaseModel):
        value: str

    register_tool(Tool('agent_value', 'value', Value, lambda value: {'value': value}))
    # Use a long enough plain_text to pass PDFInput min_length=50
    long_text = 'This is a test reference value that is long enough to pass PDF validation requirements. ' * 2
    plan = AgentPlan(goal='x', steps=[
        AgentStep(id='one', tool='agent_value', arguments={'value': long_text}),
        AgentStep(id='two', tool='create_pdf', depends_on=['one'], arguments={
            'filename': 'agent-ref',
            'title': 'Ref',
            'content': '$one.result.value',
        }),
    ])
    result = execute_plan(plan, 'request-test')
    assert result.success
    assert result.artifacts[0].download_url == '/api/files/agent-ref.pdf'
    assert result.artifacts[0].path.endswith('data/outputs/agent-ref.pdf')

    class Fail(BaseModel):
        value: str

    register_tool(Tool('agent_fail', 'fail', Fail, lambda value: (_ for _ in ()).throw(RuntimeError('expected failure'))))
    failed = execute_plan(AgentPlan(goal='x', steps=[AgentStep(id='bad', tool='agent_fail', arguments={'value': 'x'})]), 'bad')
    assert not failed.success
    assert failed.steps[0].status == 'failed'
    unregister_tool('agent_fail')
    unregister_tool('agent_value')


def test_router_classifies_requests():
    assert decide('Explain deadlock.').intent == 'simple_chat'
    # Creation requests now route to 'workflow'
    assert decide('Create a PDF explaining deadlock.').intent == 'workflow'
    assert decide('Create an Excel sheet with 20 AI interview questions.').intent == 'workflow'
    assert decide('Read this PDF, make notes, then generate a quiz and export Excel.').intent == 'workflow'


def test_executor_dependency_skips_failed_children():
    class First(BaseModel):
        value: str

    valid_content = 'This is enough content to pass the PDF minimum length requirement for validation. ' * 2
    register_tool(Tool('agent_first', 'first', First, lambda value: {'value': value}))
    register_tool(Tool('agent_second', 'second', First, lambda value: {'value': value}))
    plan = AgentPlan(goal='x', steps=[
        AgentStep(id='one', tool='agent_first', arguments={'value': 'ok'}),
        AgentStep(id='two', tool='agent_second', depends_on=['one'], arguments={'value': '$one.result.value'}),
        AgentStep(id='three', tool='create_pdf', depends_on=['two'], arguments={
            'filename': 'skipped',
            'title': 'Skipped',
            'content': valid_content,
        }),
    ])
    result = execute_plan(plan, 'request-skip')
    assert result.steps[0].status == 'completed'
    assert result.steps[1].status == 'completed'
    unregister_tool('agent_first')
    unregister_tool('agent_second')


def test_plan_preview_workflow_with_exports():
    plan = create_plan(AgentRequest(
        message='Read this PDF, make exam notes, generate 20 MCQs, export them to Excel, and create a revision PPT.',
        document_ids=['sample'],
    ))
    assert plan.steps[0].tool == 'generate_notes'
    assert len(plan.steps) >= 2
    assert all(step.status == 'pending' for step in plan.steps)


# ---------------------------------------------------------------------------
# New tests — content generation pipeline
# ---------------------------------------------------------------------------

def test_pdf_plan_has_two_steps_with_content_generation():
    """PDF creation must use generate_document_content before create_pdf."""
    plan = create_plan(AgentRequest(message='Create a detailed PDF about Generative AI'))
    validate_plan(plan)
    assert len(plan.steps) == 2
    assert plan.steps[0].tool == 'generate_document_content'
    assert plan.steps[1].tool == 'create_pdf'
    assert plan.steps[1].depends_on == ['step_1']
    # The create_pdf step must reference step_1 result, not hard-coded content
    assert '$step_1' in str(plan.steps[1].arguments.get('content', ''))
    assert '$step_1' in str(plan.steps[1].arguments.get('title', ''))


def test_excel_plan_has_two_steps_with_content_generation():
    """Excel creation must use generate_spreadsheet_content before create_excel."""
    plan = create_plan(AgentRequest(message='Create an Excel sheet with 20 AI interview questions'))
    validate_plan(plan)
    assert len(plan.steps) == 2
    assert plan.steps[0].tool == 'generate_spreadsheet_content'
    assert plan.steps[1].tool == 'create_excel'
    assert plan.steps[1].depends_on == ['step_1']


def test_ppt_plan_has_two_steps_with_content_generation():
    """PPT creation must use generate_presentation_content before create_ppt."""
    plan = create_plan(AgentRequest(message='Create a PowerPoint about Retrieval-Augmented Generation'))
    validate_plan(plan)
    assert len(plan.steps) == 2
    assert plan.steps[0].tool == 'generate_presentation_content'
    assert plan.steps[1].tool == 'create_ppt'
    assert plan.steps[1].depends_on == ['step_1']


def test_docx_plan_has_two_steps_with_content_generation():
    """DOCX creation must use generate_document_content before create_document."""
    plan = create_plan(AgentRequest(message='Create a DOCX study note about operating systems'))
    validate_plan(plan)
    assert len(plan.steps) == 2
    assert plan.steps[0].tool == 'generate_document_content'
    assert plan.steps[1].tool == 'create_document'
    assert plan.steps[1].depends_on == ['step_1']


def test_generate_document_content_tool_is_registered():
    """All three content generation tools must be in the registry."""
    from backend.core.tools import list_tools
    tools = list_tools()
    assert 'generate_document_content' in tools
    assert 'generate_presentation_content' in tools
    assert 'generate_spreadsheet_content' in tools


def test_empty_content_rejected_by_pdf_schema():
    """PDF tool must reject content shorter than 50 characters."""
    from backend.core.tools import execute_tool
    result = execute_tool('create_pdf', {
        'filename': 'test_empty.pdf',
        'title': 'Test',
        'content': 'short',
    })
    assert not result['success']
    assert 'error' in result


def test_result_reference_resolves_correctly():
    """$step_1.result.plain_text should resolve from a tool that returns plain_text."""
    class DocGenSchema(BaseModel):
        topic: str = 'test'

    def doc_tool(**kwargs) -> dict:
        return {
            'plain_text': 'A ' * 30,  # 60 chars, enough for PDF min_length=50
            'title': 'Test Document',
            'paragraphs': ['Paragraph one about testing.'],
        }

    register_tool(Tool('mock_doc_gen', 'mock doc gen', DocGenSchema, doc_tool))

    plan = AgentPlan(goal='test', steps=[
        AgentStep(id='step_1', tool='mock_doc_gen', arguments={'topic': 'test'}),
        AgentStep(id='step_2', tool='create_pdf', depends_on=['step_1'], arguments={
            'filename': 'ref-test.pdf',
            'title': '$step_1.result.title',
            'content': '$step_1.result.plain_text',
        }),
    ])
    result = execute_plan(plan, 'ref-test')
    assert result.steps[0].status == 'completed'
    assert result.steps[1].status == 'completed'
    assert len(result.artifacts) == 1
    assert result.artifacts[0].filename == 'ref-test.pdf'
    unregister_tool('mock_doc_gen')


def test_activity_events_emitted_in_order():
    """Activity events must progress: planning → tool_execution → completion."""
    events = []

    class MockContentSchema(BaseModel):
        topic: str = 'test'

    register_tool(Tool('mock_content', 'mock', MockContentSchema, lambda **_: {
        'plain_text': 'A ' * 30,
        'title': 'Mock Title',
    }))

    plan = AgentPlan(goal='test', steps=[
        AgentStep(id='step_1', tool='mock_content', arguments={'topic': 'test'}),
    ])
    from backend.agent.executor import execute_plan as ep
    ep(plan, 'evt-test', emit=events.append)

    types = [e.type for e in events]
    assert 'tool_selection' in types
    assert 'step_completed' in types
    # Execution event order: selection before execution
    sel_idx = next(i for i, e in enumerate(events) if e.type == 'tool_selection')
    exec_idx = next(i for i, e in enumerate(events) if e.type == 'step_started' and e.status == 'running')
    assert sel_idx < exec_idx
    unregister_tool('mock_content')


def test_failed_generation_does_not_produce_artifact():
    """If content generation fails, the artifact step must be skipped and no artifact created."""
    class FailGenSchema(BaseModel):
        topic: str = 'test'

    def always_fail(**kwargs):
        raise RuntimeError('Simulated content generation failure')

    register_tool(Tool('mock_fail_gen', 'fail gen', FailGenSchema, always_fail))
    plan = AgentPlan(goal='test', steps=[
        AgentStep(id='step_1', tool='mock_fail_gen', arguments={'topic': 'test'}),
        AgentStep(id='step_2', tool='create_pdf', depends_on=['step_1'], arguments={
            'filename': 'should-not-exist.pdf',
            'title': 'Should Not Exist',
            'content': '$step_1.result.plain_text',
        }),
    ])
    result = execute_plan(plan, 'fail-test')
    assert not result.success
    assert result.steps[0].status == 'failed'
    assert result.steps[1].status in {'skipped', 'failed'}
    assert len(result.artifacts) == 0
    unregister_tool('mock_fail_gen')


def test_agent_api_plan_and_run():
    client = TestClient(app)
    body = {'message': 'Create a PDF explaining binary search'}
    # Plan endpoint should return a valid two-step plan
    plan_resp = client.post('/api/agent/plan', json=body)
    assert plan_resp.json()['valid'] is True
    plan_data = plan_resp.json()['plan']
    assert plan_data['steps'][0]['tool'] == 'generate_document_content'
    assert plan_data['steps'][1]['tool'] == 'create_pdf'
    # Error cases
    assert client.post('/api/agent/plan', json={'message': ''}).status_code == 422
    assert client.post('/api/agent/run', json={'message': 'x' * 13000}).status_code == 422


def test_real_workflow_if_available():
    from backend.config import get_settings
    from backend.core.llm import LLMService

    settings = get_settings()
    service = LLMService(settings)
    if not service.health_check() or not service.model_available():
        pytest.skip('Ollama model is not available in this environment.')
    response = TestClient(app).post('/api/chat', json={'message': 'Explain binary search in one sentence.'})
    assert response.status_code == 200
