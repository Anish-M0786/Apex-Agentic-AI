from backend.intelligence.base import generate
from backend.intelligence.models import StudyGuide
def generate_study_guide(document_id:str)->StudyGuide: return generate(document_id,'study_guide',StudyGuide,'Create a source-grounded study guide. Do not call anything an actual or important exam question.')
