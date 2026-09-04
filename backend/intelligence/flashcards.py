from backend.intelligence.base import generate
from backend.intelligence.models import Flashcards
def generate_flashcards(document_id:str,count:int=20)->Flashcards:
 if not 1<=count<=100: raise ValueError('count must be between 1 and 100')
 return generate(document_id,'flashcards',Flashcards,f'Generate at most {count} non-trivial and non-duplicate flashcards covering definitions, concepts, comparisons, formulas, algorithms and important facts.',str(count),count)
