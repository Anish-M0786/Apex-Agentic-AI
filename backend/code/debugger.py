from backend.code.base import generate
from backend.code.models import DebugResult
from backend.utils.code_utils import validate_code,validate_language
def debug_code(code:str,language:str|None=None,error_message:str='',expected_behavior:str='')->DebugResult:
 code=validate_code(code); language=validate_language(language,code)
 return generate('debug',DebugResult,'Perform static analysis only. Identify likely issues and supply a corrected version. Explicitly do not claim execution.',language,code,expected_behavior,error_message)
