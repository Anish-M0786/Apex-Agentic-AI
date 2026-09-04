"""Comprehensive test suite for Apex Phase 7 — AI Runtime & Model Management.

Tests cover: provider, configuration, validation, model manager, retry,
metrics, API endpoints, structured generation, and real Qwen integration.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from backend.runtime.models import (
    GenerationRequest,
    GenerationResponse,
    ModelInfo,
    RuntimeMessage,
    StructuredGenerationRequest,
    Usage,
)
from backend.runtime.metrics import RuntimeMetrics
from backend.runtime.validation import (
    parse_structured,
    validate_response,
    _attempt_repair,
    _extract_json_substring,
)


# =========================================================================
# Helpers
# =========================================================================


class Payload(BaseModel):
    value: str


class NumberResult(BaseModel):
    answer: int


def _make_response(**overrides) -> GenerationResponse:
    defaults = {
        'success': True,
        'model': 'qwen2.5:3b',
        'content': '{"value": "ok"}',
        'usage': Usage(),
        'duration_ms': 100,
        'request_id': 'test-req',
    }
    defaults.update(overrides)
    return GenerationResponse(**defaults)


# =========================================================================
# Provider tests
# =========================================================================


class TestProvider:
    """Tests for the OllamaProvider."""

    def test_provider_initializes_with_host(self):
        from backend.runtime.ollama_provider import OllamaProvider
        provider = OllamaProvider(host='http://localhost:11434', timeout=30)
        assert provider._host == 'http://localhost:11434'

    def test_provider_health_returns_false_when_unavailable(self):
        from backend.runtime.ollama_provider import OllamaProvider
        provider = OllamaProvider(host='http://localhost:11434', timeout=2)
        provider.client = MagicMock()
        provider.client.list.side_effect = ConnectionError('refused')
        assert provider.health() is False

    def test_provider_list_models_returns_empty_when_unavailable(self):
        from backend.runtime.ollama_provider import OllamaProvider
        provider = OllamaProvider(host='http://localhost:11434', timeout=2)
        provider.client = MagicMock()
        provider.client.list.side_effect = ConnectionError('refused')
        assert provider.list_models() == []

    def test_provider_model_available_returns_false_when_unavailable(self):
        from backend.runtime.ollama_provider import OllamaProvider
        provider = OllamaProvider(host='http://localhost:11434', timeout=2)
        provider.client = MagicMock()
        provider.client.list.side_effect = ConnectionError('refused')
        assert provider.model_available('any-model') is False


# =========================================================================
# Configuration tests
# =========================================================================


class TestConfiguration:
    """Tests for configuration validation."""

    def test_valid_settings_load(self):
        """Default settings should load without error."""
        from backend.config import Settings
        s = Settings()
        assert s.ollama_model == 'qwen2.5:3b'
        assert 0.0 <= s.llm_temperature <= 2.0
        assert 0.0 < s.llm_top_p <= 1.0
        assert s.llm_top_k >= 1
        assert 512 <= s.llm_num_ctx <= 32768
        assert 1 <= s.llm_max_tokens <= 4096
        assert 5 <= s.llm_timeout_seconds <= 600
        assert 0 <= s.llm_max_retries <= 5

    def test_invalid_temperature_rejected(self, monkeypatch):
        monkeypatch.setenv('LLM_TEMPERATURE', '3.0')
        from backend.config import Settings
        with pytest.raises(ValueError, match='LLM_TEMPERATURE'):
            Settings()

    def test_invalid_max_tokens_rejected(self, monkeypatch):
        monkeypatch.setenv('LLM_MAX_TOKENS', '0')
        from backend.config import Settings
        with pytest.raises(ValueError, match='LLM_MAX_TOKENS'):
            Settings()

    def test_invalid_timeout_rejected(self, monkeypatch):
        monkeypatch.setenv('LLM_TIMEOUT_SECONDS', '2')
        from backend.config import Settings
        with pytest.raises(ValueError, match='LLM_TIMEOUT_SECONDS'):
            Settings()


# =========================================================================
# Validation tests
# =========================================================================


class TestValidation:
    """Tests for response validation and structured output parsing."""

    def test_valid_response_passes(self):
        response = _make_response(content='Hello world')
        validate_response(response)  # should not raise

    def test_empty_response_raises(self):
        with pytest.raises(ValueError, match='empty'):
            validate_response(_make_response(content=''))

    def test_whitespace_only_response_raises(self):
        with pytest.raises(ValueError, match='empty'):
            validate_response(_make_response(content='   \n  '))

    def test_oversized_response_raises(self):
        with pytest.raises(ValueError, match='size limit'):
            validate_response(_make_response(content='x' * 300_000))

    def test_parse_structured_valid_json(self):
        result = parse_structured('{"value": "hello"}', Payload)
        assert result.value == 'hello'

    def test_parse_structured_with_markdown_fences(self):
        result = parse_structured('```json\n{"value": "fenced"}\n```', Payload)
        assert result.value == 'fenced'

    def test_parse_structured_malformed_raises(self):
        with pytest.raises(ValueError):
            parse_structured('not json at all', Payload)

    def test_parse_structured_trailing_comma_repair(self):
        """Trailing commas should be repaired in one attempt."""
        result = parse_structured('{"value": "repaired",}', Payload)
        assert result.value == 'repaired'

    def test_parse_structured_schema_mismatch_raises(self):
        with pytest.raises(ValueError, match='schema validation'):
            parse_structured('{"wrong_field": "data"}', Payload)

    def test_extract_json_no_json_raises(self):
        with pytest.raises(ValueError, match='no JSON found'):
            _extract_json_substring('plain text with no braces')

    def test_attempt_repair_removes_comments(self):
        repaired = _attempt_repair('{"key": "val"} // comment')
        assert repaired is not None


# =========================================================================
# Model Manager tests
# =========================================================================


class TestModelManager:
    """Tests for the ModelManager."""

    def test_configured_model(self):
        from backend.runtime.config import RuntimeConfig
        from backend.runtime.manager import ModelManager
        config = RuntimeConfig()
        mock_provider = MagicMock()
        mock_provider.list_models.return_value = []
        mock_provider.model_available.return_value = False
        manager = ModelManager(config=config, provider=mock_provider)
        assert manager.configured_model == config.model

    def test_select_unavailable_model_raises(self):
        from backend.runtime.config import RuntimeConfig
        from backend.runtime.manager import ModelManager
        mock_provider = MagicMock()
        mock_provider.model_available.return_value = False
        manager = ModelManager(config=RuntimeConfig(), provider=mock_provider)
        with pytest.raises(ValueError, match='not available'):
            manager.select('nonexistent-model')

    def test_select_available_model_succeeds(self):
        from backend.runtime.config import RuntimeConfig
        from backend.runtime.manager import ModelManager
        mock_provider = MagicMock()
        mock_provider.model_available.return_value = True
        manager = ModelManager(config=RuntimeConfig(), provider=mock_provider)
        assert manager.select('qwen2.5:3b') == 'qwen2.5:3b'


# =========================================================================
# Retry tests
# =========================================================================


class TestRetry:
    """Tests for retry behavior in the AIRuntime."""

    def _make_runtime(self, max_retries=1, has_fallback=False):
        from backend.runtime.config import RuntimeConfig
        from backend.runtime.generation import AIRuntime
        from backend.runtime.manager import ModelManager

        config = RuntimeConfig()
        config.max_retries = max_retries
        if not has_fallback:
            config.fallback_model = ''

        mock_provider = MagicMock()
        mock_provider.model_available.return_value = True
        mock_provider.health.return_value = True

        manager = ModelManager(config=config, provider=mock_provider)
        runtime = AIRuntime(manager=manager)
        return runtime, mock_provider

    def test_transient_failure_retries_and_succeeds(self):
        runtime, mock_provider = self._make_runtime(max_retries=1)
        good_response = _make_response(content='success')
        mock_provider.generate.side_effect = [
            ConnectionError('timeout'),
            good_response,
        ]
        result = runtime.generate(
            GenerationRequest(messages=[RuntimeMessage(role='user', content='hi')])
        )
        assert result.content == 'success'
        assert mock_provider.generate.call_count == 2

    def test_retry_limit_exhausted_raises_runtime_error(self):
        runtime, mock_provider = self._make_runtime(max_retries=1)
        mock_provider.generate.side_effect = ConnectionError('timeout')
        with pytest.raises(RuntimeError, match='Generation provider failure'):
            runtime.generate(
                GenerationRequest(messages=[RuntimeMessage(role='user', content='hi')])
            )
        # 1 initial + 1 retry = 2 attempts
        assert mock_provider.generate.call_count == 2

    def test_permanent_failure_does_not_retry(self):
        runtime, mock_provider = self._make_runtime(max_retries=2)
        mock_provider.generate.side_effect = ValueError('Invalid model')
        with pytest.raises(ValueError, match='Invalid model'):
            runtime.generate(
                GenerationRequest(messages=[RuntimeMessage(role='user', content='hi')])
            )
        # ValueError should NOT be retried
        assert mock_provider.generate.call_count == 1


# =========================================================================
# Metrics tests
# =========================================================================


class TestMetrics:
    """Tests for RuntimeMetrics."""

    def test_request_count_increments(self):
        m = RuntimeMetrics()
        m.record(True, 10, 'model-a')
        m.record(True, 20, 'model-a')
        assert m.snapshot()['request_count'] == 2

    def test_success_and_failure_counts(self):
        m = RuntimeMetrics()
        m.record(True, 10, 'qwen')
        m.record(False, 30, 'qwen')
        data = m.snapshot()
        assert data['successful_requests'] == 1
        assert data['failed_requests'] == 1

    def test_average_latency(self):
        m = RuntimeMetrics()
        m.record(True, 10, 'qwen')
        m.record(False, 30, 'qwen')
        assert m.snapshot()['average_latency_ms'] == 20.0

    def test_reset_clears_all(self):
        m = RuntimeMetrics()
        m.record(True, 100, 'qwen')
        m.reset()
        data = m.snapshot()
        assert data['request_count'] == 0
        assert data['successful_requests'] == 0


# =========================================================================
# API endpoint tests
# =========================================================================


class TestRuntimeAPI:
    """Tests for the runtime API endpoints."""

    def _client(self):
        from backend.main import app
        return TestClient(app)

    def test_runtime_health_returns_200(self):
        client = self._client()
        resp = client.get('/api/runtime/health')
        assert resp.status_code == 200
        data = resp.json()
        assert 'provider' in data
        assert 'available' in data
        assert 'configured_model' in data

    def test_runtime_models_returns_200_or_503(self):
        client = self._client()
        resp = client.get('/api/runtime/models')
        assert resp.status_code in {200, 503}

    def test_runtime_test_empty_message_returns_422(self):
        client = self._client()
        resp = client.post('/api/runtime/test', json={'message': ''})
        assert resp.status_code == 422

    def test_existing_health_still_works(self):
        client = self._client()
        resp = client.get('/health')
        assert resp.status_code == 200
        data = resp.json()
        assert 'status' in data

    def test_existing_root_still_works(self):
        client = self._client()
        resp = client.get('/')
        assert resp.status_code == 200
        assert resp.json() == {'name': 'Apex', 'status': 'running'}


# =========================================================================
# Structured generation tests
# =========================================================================


class TestStructuredGeneration:
    """Tests for structured generation parsing."""

    def test_valid_json_parsed_to_model(self):
        result = parse_structured('{"value": "structured"}', Payload)
        assert isinstance(result, Payload)
        assert result.value == 'structured'

    def test_json_with_extra_text_parsed(self):
        result = parse_structured(
            'Here is the result: {"value": "extracted"} -- done',
            Payload,
        )
        assert result.value == 'extracted'


# =========================================================================
# Model validation tests
# =========================================================================


class TestModels:
    """Tests for Pydantic model validation."""

    def test_generation_request_requires_messages(self):
        with pytest.raises(Exception):
            GenerationRequest(messages=[])

    def test_runtime_message_role_validation(self):
        RuntimeMessage(role='user', content='hello')
        RuntimeMessage(role='system', content='prompt')
        RuntimeMessage(role='assistant', content='reply')
        with pytest.raises(ValueError, match='Role must be'):
            RuntimeMessage(role='admin', content='bad')

    def test_generation_request_temperature_bounds(self):
        GenerationRequest(
            messages=[RuntimeMessage(role='user', content='hi')],
            temperature=0.5,
        )
        with pytest.raises(Exception):
            GenerationRequest(
                messages=[RuntimeMessage(role='user', content='hi')],
                temperature=3.0,
            )

    def test_structured_generation_request_has_schema_field(self):
        req = StructuredGenerationRequest(
            messages=[RuntimeMessage(role='user', content='hi')],
            response_schema={'type': 'object'},
        )
        assert req.response_schema == {'type': 'object'}

    def test_model_info(self):
        info = ModelInfo(name='qwen2.5:3b', size=1900000000)
        assert info.name == 'qwen2.5:3b'
        assert info.size == 1900000000


# =========================================================================
# Real Qwen integration test (skipped if Ollama unavailable)
# =========================================================================


class TestRealIntegration:
    """Integration tests that require a running Ollama instance.

    These tests are automatically skipped if Ollama is not reachable.
    """

    def _skip_if_no_ollama(self):
        from backend.core.llm import LLMService
        service = LLMService()
        if not service.health_check() or not service.model_available():
            pytest.skip('Ollama model is not available in this environment.')

    def test_real_qwen_via_runtime_test_endpoint(self):
        self._skip_if_no_ollama()
        from backend.main import app
        client = TestClient(app)
        resp = client.post(
            '/api/runtime/test',
            json={'message': 'Explain binary search in one sentence.'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['model'] == 'qwen2.5:3b'
        assert len(data['response']) > 0

    def test_real_qwen_via_chat_endpoint(self):
        self._skip_if_no_ollama()
        from backend.main import app
        client = TestClient(app)
        resp = client.post(
            '/api/chat',
            json={'message': 'Say hello in one sentence.'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert len(data['response']) > 0
