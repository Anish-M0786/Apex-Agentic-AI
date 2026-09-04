from backend.intelligence.base import generate
from backend.intelligence.models import Questions
def generate_questions(document_id:str,question_type:str='short_answer',count:int=10)->Questions:
 if question_type not in {'short_answer','long_answer','conceptual','definition','application'} or not 1<=count<=100: raise ValueError('Invalid question configuration')
 return generate(document_id,'questions',Questions,f'Generate at most {count} source-grounded {question_type} study questions. These are practice questions, not claims about actual exams.',question_type,count)
