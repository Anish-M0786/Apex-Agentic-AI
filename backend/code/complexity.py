from backend.code.base import generate
from backend.code.models import ComplexityAnalysis
from backend.utils.code_utils import validate_code,validate_language
def analyze_complexity(code:str,language:str|None=None)->ComplexityAnalysis:
 code=validate_code(code); language=validate_language(language,code)
 return generate('complexity',ComplexityAnalysis,'Provide static complexity analysis. Clearly distinguish worst-case, average-case and best-case only where meaningful; do not invent claims.',language,code)
