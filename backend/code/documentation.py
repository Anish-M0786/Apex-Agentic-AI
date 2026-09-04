from backend.code.base import generate
from backend.code.models import Documentation
from backend.utils.code_utils import validate_code,validate_language
def generate_documentation(code:str,language:str|None=None,style:str='standard')->Documentation:
 code=validate_code(code); language=validate_language(language,code)
 return generate('documentation',Documentation,'Generate overview, API or function documentation, parameters, returns, usage, assumptions and limitations in the requested style.',language,code,style)
