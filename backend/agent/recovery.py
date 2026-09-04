from __future__ import annotations

from backend.config import get_settings


def retry_allowed(attempt: int, error: str) -> bool:
	maximum = getattr(get_settings(), 'agent_max_retries', 1)
	normalized = error.lower()
	if attempt >= maximum:
		return False
	if 'invalid tool input' in normalized:
		return False
	if 'not found' in normalized:
		return False
	if 'unsupported' in normalized or 'dangerous' in normalized:
		return False
	return True
