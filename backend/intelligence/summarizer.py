from backend.intelligence.base import generate
from backend.intelligence.models import Summary
def summarize_document(document_id:str,mode:str='balanced')->Summary:
 if mode not in {'concise','balanced','detailed'}: raise ValueError('Invalid summary mode')
 return generate(document_id,'summary',Summary,f'Create a {mode} factual document summary.',mode)
