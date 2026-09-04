from backend.code.base import generate
from backend.code.models import TestGeneration
from backend.utils.code_utils import validate_code,validate_language
def generate_tests(code:str,language:str|None=None,framework:str='')->TestGeneration:
 code=validate_code(code); language=validate_language(language,code)
 defaults={'python':'pytest','java':'JUnit','javascript':'Jest','typescript':'Jest','c':'basic test driver','cpp':'basic test driver'}
 framework=framework or defaults.get(language,'basic test driver')
 return generate('tests',TestGeneration,'Generate normal, edge, boundary, invalid and empty-input tests where relevant. Clearly state generated tests have not run.',language,code,framework)
