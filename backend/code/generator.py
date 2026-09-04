from backend.code.base import generate
from backend.code.models import CodeGeneration
from backend.utils.code_utils import validate_language
def generate_code(language:str,task:str,constraints:str='',existing_code:str='')->CodeGeneration:
 language=validate_language(language,existing_code)
 if not task.strip(): raise ValueError('task must not be empty')
 return generate('generate',CodeGeneration,'Generate concise, dependency-light code that follows constraints. State assumptions and do not claim it is verified.',language,existing_code,task+'\nConstraints: '+constraints)
