from backend.code.base import generate
from backend.code.models import ReviewResult
from backend.utils.code_utils import validate_code,validate_language
def review_code(code:str,language:str|None=None)->ReviewResult:
 code=validate_code(code); language=validate_language(language,code)
 return generate('review',ReviewResult,'Review static correctness risks, readability, maintainability, performance, supported security concerns, duplication, errors, naming and unnecessary complexity. Do not make unsupported claims.',language,code)
