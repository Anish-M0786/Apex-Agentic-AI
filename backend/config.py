"""Application configuration loaded from environment variables."""

from functools import lru_cache
import os

from dotenv import load_dotenv


class Settings:
    """Apex application settings.

    All values are loaded from environment variables with sensible
    CPU-friendly defaults for an 8 GB RAM machine running Ollama.
    """

    def __init__(self) -> None:
        load_dotenv()

        # ---- Ollama provider ------------------------------------------------
        self.ollama_host: str = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.ollama_model: str = os.getenv('OLLAMA_MODEL', 'qwen2.5:3b')
        self.ollama_embed_model: str = os.getenv('OLLAMA_EMBED_MODEL', '')
        self.ollama_fallback_model: str = os.getenv('OLLAMA_FALLBACK_MODEL', '')

        # ---- LLM generation parameters -------------------------------------
        self.llm_temperature: float = float(os.getenv('LLM_TEMPERATURE', '0.2'))
        self.llm_top_p: float = float(os.getenv('LLM_TOP_P', '0.9'))
        self.llm_top_k: int = int(os.getenv('LLM_TOP_K', '40'))
        self.llm_num_ctx: int = int(os.getenv('LLM_NUM_CTX', '3072'))
        self.llm_max_tokens: int = int(os.getenv('LLM_MAX_TOKENS', '768'))
        self.llm_timeout_seconds: int = int(os.getenv('LLM_TIMEOUT_SECONDS', '120'))
        self.llm_max_retries: int = int(os.getenv('LLM_MAX_RETRIES', '0'))

        # ---- Validate LLM parameters ---------------------------------------
        self._validate_llm_params()

        # ---- Intelligence settings ------------------------------------------
        self.intelligence_chunk_chars: int = int(os.getenv('INTELLIGENCE_CHUNK_CHARS', '5000'))
        self.intelligence_max_chunks: int = int(os.getenv('INTELLIGENCE_MAX_CHUNKS', '40'))

        # ---- Code Intelligence settings -------------------------------------
        self.code_max_input_chars: int = int(os.getenv('CODE_MAX_INPUT_CHARS', '30000'))
        self.code_cache_enabled: bool = os.getenv('CODE_CACHE_ENABLED', 'true').lower() in {
            '1', 'true', 'yes',
        }

        # ---- Agent settings -------------------------------------------------
        self.agent_max_steps: int = int(os.getenv('AGENT_MAX_STEPS', '10'))
        self.agent_max_retries: int = int(os.getenv('AGENT_MAX_RETRIES', '1'))
        self.agent_timeout_seconds: int = int(os.getenv('AGENT_TIMEOUT_SECONDS', '300'))

    def _validate_llm_params(self) -> None:
        """Validate each LLM parameter individually with clear error messages."""
        if not (0.0 <= self.llm_temperature <= 2.0):
            raise ValueError(
                f'LLM_TEMPERATURE must be between 0.0 and 2.0, got {self.llm_temperature}'
            )
        if not (0.0 < self.llm_top_p <= 1.0):
            raise ValueError(
                f'LLM_TOP_P must be between 0.0 (exclusive) and 1.0, got {self.llm_top_p}'
            )
        if self.llm_top_k < 1:
            raise ValueError(
                f'LLM_TOP_K must be >= 1, got {self.llm_top_k}'
            )
        if not (512 <= self.llm_num_ctx <= 32768):
            raise ValueError(
                f'LLM_NUM_CTX must be between 512 and 32768, got {self.llm_num_ctx}'
            )
        if not (1 <= self.llm_max_tokens <= 4096):
            raise ValueError(
                f'LLM_MAX_TOKENS must be between 1 and 4096, got {self.llm_max_tokens}'
            )
        if not (5 <= self.llm_timeout_seconds <= 600):
            raise ValueError(
                f'LLM_TIMEOUT_SECONDS must be between 5 and 600, got {self.llm_timeout_seconds}'
            )
        if not (0 <= self.llm_max_retries <= 5):
            raise ValueError(
                f'LLM_MAX_RETRIES must be between 0 and 5, got {self.llm_max_retries}'
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
