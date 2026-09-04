from backend.intelligence.base import generate
from backend.intelligence.models import Notes
def generate_notes(document_id:str,style:str='exam')->Notes:
 if style not in {'exam','detailed','quick_revision','beginner'}: raise ValueError('Invalid notes style')
 return generate(document_id,'notes',Notes,f'Create {style} notes. For exam style prioritize definitions, concepts, formulas, algorithms, examples, comparisons, advantages and disadvantages.',style)
def generate_semester_notes(document_id:str)->Notes: return generate(document_id,'semester_notes',Notes,'Organize source-supported units or chapters into sections. Include explanation, important points, examples, and exam focus only when source-supported.')
