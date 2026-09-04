"""Small local memory and preference store for the single-user Apex workspace."""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parents[2]
MEMORY_FILE = ROOT / 'data' / 'apex_memory.json'
_lock = Lock()

def _read() -> dict:
    if not MEMORY_FILE.is_file():
        return {'facts': [], 'preferences': [], 'themes': [], 'feedback': []}
    try:
        return json.loads(MEMORY_FILE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'facts': [], 'preferences': [], 'themes': [], 'feedback': []}

def _write(data: dict) -> None:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def context() -> str:
    with _lock:
        data = _read()
    parts = []
    if data.get('facts'):
        parts.append('Known user details: ' + '; '.join(data['facts'][-10:]))
    if data.get('preferences'):
        parts.append('User preferences: ' + '; '.join(data['preferences'][-10:]))
    if data.get('themes'):
        parts.append('Recent interests: ' + ', '.join(data['themes'][-10:]))
    return '\n'.join(parts)

def learn_from_message(message: str) -> None:
    lower = message.lower()
    themes = [word for word in re.findall(r'\b[a-zA-Z][a-zA-Z-]{3,}\b', lower)
              if word not in {'what', 'this', 'that', 'with', 'from', 'about', 'please'}]
    with _lock:
        data = _read()
        data['themes'] = list(dict.fromkeys(data.get('themes', []) + themes[-4:]))[-30:]
        name = re.search(r"\bmy name is ([A-Za-z][A-Za-z .'-]{1,40})", message, re.I)
        if name:
            fact = 'user name is ' + name.group(1).strip()
            data['facts'] = [item for item in data.get('facts', []) if not item.startswith('user name is ')] + [fact]
        _write(data)

def save_feedback(message: str, response: str, rating: str, comment: str = '') -> None:
    with _lock:
        data = _read()
        data.setdefault('feedback', []).append({
            'message': message[:4000], 'response': response[:8000],
            'rating': rating, 'comment': comment[:1000],
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
        data['feedback'] = data['feedback'][-200:]
        _write(data)
