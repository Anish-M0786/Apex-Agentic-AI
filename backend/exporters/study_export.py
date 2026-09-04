from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel
from backend.generators.pdf import create_pdf
from backend.generators.document import create_document
from backend.generators.excel import create_excel
from backend.generators.ppt import create_ppt
def _lines(value:object,prefix:str='')->list[str]:
 if isinstance(value,dict): return [f'{prefix}{k}: '+(', '.join(map(str,v)) if isinstance(v,list) else str(v)) for k,v in value.items()]
 return [str(value)]
def export_study_result(result:BaseModel,format:str,filename:str)->dict[str,object]:
 if format not in {'pdf','docx','pptx','xlsx'}: raise ValueError('Unsupported export format')
 data=result.model_dump(); title=str(data.get('title') or result.__class__.__name__); lines=_lines(data)
 if format=='pdf': return create_pdf(filename,title,'\n'.join(lines))
 if format=='docx': return create_document(filename,title,lines)
 if format=='pptx': return create_ppt(filename,title,[{'title':title,'bullet_points':lines}])
 if 'questions' in data:
  rows=[[q.get('question',''),' | '.join(q.get('options',[])),q.get('answer',''),q.get('explanation',''),q.get('topic',''),q.get('difficulty','')] for q in data['questions']]
  return create_excel(filename,'Quiz',['Question','Options','Answer','Explanation','Topic','Difficulty'],rows)
 if 'cards' in data: return create_excel(filename,'Flashcards',['Question','Answer'],[[x['question'],x['answer']] for x in data['cards']])
 return create_excel(filename,'Study Result',['Field','Value'],[[x.split(':',1)[0],x.split(':',1)[-1].strip()] for x in lines])
