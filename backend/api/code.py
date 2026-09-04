from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from backend.code.generator import generate_code
from backend.code.analyzer import explain_code
from backend.code.debugger import debug_code
from backend.code.refactor import refactor_code
from backend.code.reviewer import review_code
from backend.code.tests_generator import generate_tests
from backend.code.documentation import generate_documentation
from backend.code.complexity import analyze_complexity
router=APIRouter(prefix='/api/code',tags=['code'])
class GenerateRequest(BaseModel): language:str; task:str=Field(min_length=1,max_length=10000); constraints:str=''; existing_code:str=''
class CodeRequest(BaseModel): code:str=Field(min_length=1); language:str|None=None
class ExplainRequest(CodeRequest): level:str='intermediate'
class DebugRequest(CodeRequest): error_message:str=''; expected_behavior:str=''
class RefactorRequest(CodeRequest): goal:str='readability'
class TestsRequest(CodeRequest): framework:str=''
class DocumentRequest(CodeRequest): style:str='standard'
def invoke(fn,*args):
 try:return fn(*args).model_dump()
 except ValueError as exc: raise HTTPException(422,str(exc))
 except Exception: raise HTTPException(503,'Code intelligence generation failed.')
@router.post('/generate')
def generate(r:GenerateRequest): return invoke(generate_code,r.language,r.task,r.constraints,r.existing_code)
@router.post('/explain')
def explain(r:ExplainRequest): return invoke(explain_code,r.code,r.language,r.level)
@router.post('/debug')
def debug(r:DebugRequest): return invoke(debug_code,r.code,r.language,r.error_message,r.expected_behavior)
@router.post('/refactor')
def refactor(r:RefactorRequest): return invoke(refactor_code,r.code,r.language,r.goal)
@router.post('/review')
def review(r:CodeRequest): return invoke(review_code,r.code,r.language)
@router.post('/tests')
def tests(r:TestsRequest): return invoke(generate_tests,r.code,r.language,r.framework)
@router.post('/document')
def document(r:DocumentRequest): return invoke(generate_documentation,r.code,r.language,r.style)
@router.post('/complexity')
def complexity(r:CodeRequest): return invoke(analyze_complexity,r.code,r.language)
