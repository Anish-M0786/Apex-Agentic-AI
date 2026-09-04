"""Security utilities for input filtering."""

import re

# Common prompt injection phrases and patterns
INJECTION_PATTERNS = [
    r"(?i)\bignore\s+(all\s+)?(previous\s+)?instructions?\b",
    r"(?i)\bsystem\s+prompt\b",
    r"(?i)\bbypass\b",
    r"(?i)\bdisregard\s+(all\s+)?previous\b",
    r"(?i)\byou\s+are\s+now\b",
    r"(?i)\bforget\s+about\b",
    r"(?i)\bexpose\s+your\s+architecture\b",
]

def check_prompt_injection(message: str) -> bool:
    """Check if the message contains potential prompt injection."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, message):
            return True
    return False

def sanitize_input(message: str) -> str:
    """Sanitize input by raising an error if it's malicious."""
    if check_prompt_injection(message):
        raise ValueError("Potential prompt injection detected. Your request has been blocked for security reasons.")
    return message
