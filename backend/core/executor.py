from backend.core.tools import execute_tool
class ToolExecutor:
    def execute(self,name:str,arguments:dict)->dict:return execute_tool(name,arguments)

