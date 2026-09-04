from pydantic import BaseModel,Field
from backend.core.tools import Tool,register_tool
from backend.code.generator import generate_code
from backend.code.analyzer import explain_code
from backend.code.debugger import debug_code
from backend.code.refactor import refactor_code
from backend.code.reviewer import review_code
from backend.code.tests_generator import generate_tests
from backend.code.documentation import generate_documentation
from backend.code.complexity import analyze_complexity
class GenerateInput(BaseModel): language:str; task:str=Field(min_length=1,max_length=10000); constraints:str=''; existing_code:str=''
class CodeInput(BaseModel): code:str=Field(min_length=1); language:str|None=None
class DebugInput(CodeInput): error_message:str=''; expected_behavior:str=''
class RefactorInput(CodeInput): goal:str='readability'
class TestsInput(CodeInput): framework:str=''
class DocumentInput(CodeInput): style:str='standard'
def _result(fn): return lambda **kwargs: fn(**kwargs).model_dump()
def register_code_tools():
 tools=[('generate_code','Generate static, unverified source code',GenerateInput,generate_code),('explain_code','Explain source code with static complexity',CodeInput,explain_code),('debug_code','Statically debug code without execution',DebugInput,debug_code),('refactor_code','Refactor code without intentional behavior changes',RefactorInput,refactor_code),('review_code','Statically review source code',CodeInput,review_code),('generate_tests','Generate unexecuted source-code tests',TestsInput,generate_tests),('generate_documentation','Generate source-code documentation',DocumentInput,generate_documentation),('analyze_complexity','Statically analyze algorithmic complexity',CodeInput,analyze_complexity)]
 for name,description,schema,fn in tools: register_tool(Tool(name,description,schema,_result(fn)))
