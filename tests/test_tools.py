from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.tools import list_tools, get_tool, register_tool, unregister_tool, Tool
from backend.core.executor import ToolExecutor
from pydantic import BaseModel

def test_registry_and_executor():
    assert 'create_pdf' in list_tools(); assert get_tool('missing') is None
    class Input(BaseModel): value:str
    register_tool(Tool('test_tool','test',Input,lambda value:{'value':value}))
    assert ToolExecutor().execute('test_tool',{'value':'ok'})['success']
    unregister_tool('test_tool')
    assert not ToolExecutor().execute('missing',{})['success']

def test_generators_and_download(tmp_path):
    # Excel: must have at least one data row
    out = ToolExecutor().execute('create_excel', {'filename': 'test-phase2', 'columns': ['A'], 'rows': [[1]]})
    assert out['success'] and Path(out['result']['file']).exists()

    # PDF: content must be at least 50 chars
    long_content = 'This is a valid test content for a PDF document that meets the minimum length requirement.'
    pdf_result = ToolExecutor().execute('create_pdf', {'filename': 'test.pdf', 'title': 'T', 'content': long_content})
    assert pdf_result['success'] and Path(pdf_result['result']['file']).exists()

    # PPT: must have at least 1 slide
    ppt_result = ToolExecutor().execute('create_ppt', {'filename': 'test.pptx', 'presentation_title': 'T', 'slides': [{'title': 'Slide 1', 'bullet_points': ['Point A', 'Point B']}]})
    assert ppt_result['success'] and Path(ppt_result['result']['file']).exists()

    # DOCX: must have at least 1 paragraph
    doc_result = ToolExecutor().execute('create_document', {'filename': 'test.docx', 'title': 'T', 'paragraphs': ['This is a content paragraph.']})
    assert doc_result['success'] and Path(doc_result['result']['file']).exists()

    client = TestClient(app)
    assert client.get('/api/files/test.pdf').status_code == 200
    assert client.get('/api/files/../requirements.txt').status_code == 404
