from fastapi.testclient import TestClient
import pytest
from backend.main import app
from backend.intelligence.models import Summary, Notes, Flashcards, Quiz, QuizQuestion
from backend.intelligence.base import document_text, cache_get, cache_put
from backend.exporters.study_export import export_study_result

def test_structured_models_and_quiz_validation():
    assert Summary(title='T',overview='O').title == 'T'
    assert Notes(title='T').sections == []
    assert Flashcards(cards=[{'question':'Q','answer':'A'}]).cards[0].answer == 'A'
    with pytest.raises(ValueError): Quiz(questions=[QuizQuestion(question='Q',options=['A','B','C','D'],answer='X',explanation='')])
    with pytest.raises(ValueError): Flashcards(cards=[{'question':'Q','answer':'1'},{'question':'q','answer':'2'}])

def test_invalid_document_id_and_api():
    with pytest.raises(ValueError): document_text('../secret')
    assert TestClient(app).post('/api/intelligence/topics',json={'document_id':'missing'}).status_code == 404

def test_cache_and_export_integration():
    cache_put('test-intelligence-cache',{'ok':True})
    assert cache_get('test-intelligence-cache') == {'ok':True}
    out=export_study_result(Summary(title='Study',overview='Overview',key_points=['Fact']),'pdf','phase4-summary')
    assert out['success']
    out=export_study_result(Summary(title='Study',overview='Overview'),'docx','phase4-summary')
    assert out['success']
    quiz=Quiz(questions=[{'question':'Q?','options':['A','B','C','D'],'answer':'A','explanation':'Source fact'}])
    assert export_study_result(quiz,'xlsx','phase4-quiz')['success']
