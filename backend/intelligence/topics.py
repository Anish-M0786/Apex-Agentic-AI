from backend.intelligence.base import generate
from backend.intelligence.models import Topics
def extract_topics(document_id:str)->Topics: return generate(document_id,'topics',Topics,'Extract major topics, concepts, and only explicitly supported units or chapters. Never fabricate unit numbers.')
