from backend.code.base import generate
from backend.code.models import ExplainCode
from backend.utils.code_utils import validate_code,validate_language
def explain_code(code:str,language:str|None=None,level:str='intermediate')->ExplainCode:
 if level not in {'beginner','intermediate','advanced'}: raise ValueError('Invalid explanation level')
 code=validate_code(code); language=validate_language(language,code)
 return generate('explain',ExplainCode,f'Explain the code for a {level} audience with step-by-step behavior, concepts, static complexity and pitfalls.',language,code,level)
