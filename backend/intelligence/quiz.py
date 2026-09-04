from backend.intelligence.base import generate
from backend.intelligence.models import Quiz
def generate_quiz(document_id:str,count:int=10,difficulty:str='mixed')->Quiz:
 if not 1<=count<=100 or difficulty not in {'easy','medium','hard','mixed'}: raise ValueError('Invalid quiz configuration')
 return generate(document_id,'quiz',Quiz,f'Generate at most {count} distinct {difficulty} multiple-choice questions. Each needs exactly four options and answer text exactly matching one option.',difficulty,count)
