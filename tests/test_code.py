from fastapi.testclient import TestClient
import pytest
from backend.main import app
from backend.core.tools import list_tools
from backend.code.models import CodeGeneration,Complexity,CodeIssue,ReviewResult,ComplexityAnalysis
from backend.utils.code_utils import validate_code,detect_language

def sample_generation(): return CodeGeneration(language='python',code='print(1)',explanation='Prints one.',complexity=Complexity(time='O(1)',space='O(1)'))
def test_models_and_severity_validation():
 assert sample_generation().language=='python'
 assert ReviewResult(summary='ok',issues=[CodeIssue(description='x',severity='warning')]).issues[0].severity=='warning'
 assert ComplexityAnalysis(worst_case='O(n)',space='O(1)',reasoning='one pass').worst_case=='O(n)'
 with pytest.raises(ValueError): CodeIssue(description='bad',severity='urgent')
def test_input_validation_and_detection(monkeypatch):
 assert detect_language('def f():\n return 1')[0]=='python'
 with pytest.raises(ValueError): validate_code('')
 from backend.utils import code_utils
 monkeypatch.setattr(code_utils.get_settings(),'code_max_input_chars',3)
 with pytest.raises(ValueError): validate_code('1234')
def test_code_tools_registered():
 names=set(list_tools())
 assert {'generate_code','explain_code','debug_code','refactor_code','review_code','generate_tests','generate_documentation','analyze_complexity'} <= names
def test_code_api_valid_and_invalid(monkeypatch):
 import backend.api.code as api
 monkeypatch.setattr(api,'generate_code',lambda *args: sample_generation())
 client=TestClient(app)
 assert client.post('/api/code/generate',json={'language':'python','task':'say hi'}).status_code==200
 assert client.post('/api/code/generate',json={'language':'python','task':''}).status_code==422
 assert client.post('/api/code/explain',json={'language':'python'}).status_code==422
