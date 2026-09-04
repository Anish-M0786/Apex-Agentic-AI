from backend.code.base import generate
from backend.code.models import RefactorResult
from backend.utils.code_utils import validate_code,validate_language
def refactor_code(code:str,language:str|None=None,goal:str='readability')->RefactorResult:
 if goal not in {'readability','simplicity','performance','maintainability','modern syntax'}: raise ValueError('Invalid refactor goal')
 code=validate_code(code); language=validate_language(language,code)
 return generate('refactor',RefactorResult,'Refactor without intentionally changing behavior; list changes and reasoning.',language,code,goal)
