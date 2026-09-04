from collections.abc import Callable
from pydantic import BaseModel, ValidationError
class Tool:
    def __init__(self,name:str,description:str,schema:type[BaseModel],execute:Callable[...,dict],enabled:bool=True)->None: self.name,self.description,self.schema,self.execute,self.enabled=name,description,schema,execute,enabled
_TOOLS:dict[str,Tool]={}
def register_tool(tool:Tool)->None: _TOOLS[tool.name]=tool
def unregister_tool(name:str)->None: _TOOLS.pop(name,None)
def get_tool(name:str)->Tool|None: return _TOOLS.get(name)
def list_tools()->list[str]: return sorted(_TOOLS)
def execute_tool(name:str,arguments:dict)->dict:
    tool=get_tool(name)
    if tool is None:return {"success":False,"tool":name,"error":"Tool not found."}
    if not tool.enabled:return {"success":False,"tool":name,"error":"Tool is disabled."}
    try:return {"success":True,"tool":name,"result":tool.execute(**tool.schema.model_validate(arguments).model_dump())}
    except ValidationError as exc:return {"success":False,"tool":name,"error":f"Invalid tool input: {exc.errors()}"}
    except Exception as exc:return {"success":False,"tool":name,"error":str(exc)}
from pydantic import Field
from backend.generators.pdf import create_pdf
from backend.generators.excel import create_excel
from backend.generators.ppt import create_ppt
from backend.generators.document import create_document

class PDFInput(BaseModel):
    filename: str
    title: str
    content: str = Field(min_length=50, description='PDF body text; must be non-trivial content')

from pydantic import model_validator

class ExcelInput(BaseModel):
    filename: str
    sheet_name: str = 'Sheet1'
    columns: list[str] = Field(default_factory=list)
    rows: list[list[object]] = Field(default_factory=list)

    @model_validator(mode='after')
    def must_have_rows(self) -> 'ExcelInput':
        if not self.rows:
            raise ValueError('Excel must have at least one data row')
        return self


class PPTInput(BaseModel):
    filename: str
    presentation_title: str
    slides: list[dict[str, object]] = Field(default_factory=list, min_length=1)

class DocumentInput(BaseModel):
    filename: str
    title: str
    paragraphs: list[str] = Field(default_factory=list, min_length=1)

register_tool(Tool('create_pdf', 'Create a PDF', PDFInput, create_pdf))
register_tool(Tool('create_excel', 'Create an Excel workbook', ExcelInput, create_excel))
register_tool(Tool('create_ppt', 'Create a PowerPoint presentation', PPTInput, create_ppt))
register_tool(Tool('create_document', 'Create a Word document', DocumentInput, create_document))
