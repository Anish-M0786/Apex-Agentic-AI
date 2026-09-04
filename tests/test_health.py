from fastapi.testclient import TestClient
from backend.main import app
client = TestClient(app)
def test_root() -> None: assert client.get("/").json() == {"name":"Apex", "status":"running"}
def test_health_does_not_crash_without_ollama(monkeypatch) -> None:
    from backend.core.llm import LLMService
    monkeypatch.setattr(LLMService, "health_check", lambda self: False)
    assert client.get("/health").status_code == 200
def test_chat_rejects_empty_message() -> None: assert client.post("/api/chat", json={"message":""}).status_code == 422
