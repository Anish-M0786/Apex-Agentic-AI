from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from backend.intelligence.summarizer import summarize_document
from backend.intelligence.topics import extract_topics
from backend.intelligence.notes import generate_notes,generate_semester_notes
from backend.intelligence.study_guide import generate_study_guide
from backend.intelligence.flashcards import generate_flashcards
from backend.intelligence.quiz import generate_quiz
from backend.intelligence.questions import generate_questions
from backend.exporters.study_export import export_study_result
router=APIRouter(prefix='/api/intelligence',tags=['intelligence'])
class DocumentRequest(BaseModel): document_id:str=Field(min_length=1,max_length=128)
class SummaryRequest(DocumentRequest): mode:str='balanced'
class NotesRequest(DocumentRequest): style:str='exam'
class CountRequest(DocumentRequest): count:int=Field(default=20,ge=1,le=100)
class QuizRequest(CountRequest): difficulty:str='mixed'
class QuestionsRequest(CountRequest): question_type:str='short_answer'
class ExportRequest(BaseModel): format:str; filename:str=Field(min_length=1,max_length=128)
def invoke(fn,*args):
 try: return fn(*args)
 except FileNotFoundError: raise HTTPException(404,'Document not found.')
 except (ValueError,RuntimeError): raise HTTPException(422,'Invalid request or unavailable document intelligence service.')
 except Exception: raise HTTPException(503,'Document intelligence generation failed.')
def response(result,export:ExportRequest|None):
 payload=result.model_dump()
 if export: payload['export']=invoke(export_study_result,result,export.format,export.filename)
 return payload
@router.post('/summarize')
def summarize(request:SummaryRequest,export:ExportRequest|None=None): return response(invoke(summarize_document,request.document_id,request.mode),export)
@router.post('/topics')
def topics(request:DocumentRequest): return invoke(extract_topics,request.document_id).model_dump()
@router.post('/notes')
def notes(request:NotesRequest,export:ExportRequest|None=None): return response(invoke(generate_notes,request.document_id,request.style),export)
@router.post('/semester-notes')
def semester_notes(request:DocumentRequest,export:ExportRequest|None=None): return response(invoke(generate_semester_notes,request.document_id),export)
@router.post('/study-guide')
def study_guide(request:DocumentRequest,export:ExportRequest|None=None): return response(invoke(generate_study_guide,request.document_id),export)
@router.post('/flashcards')
def flashcards(request:CountRequest,export:ExportRequest|None=None): return response(invoke(generate_flashcards,request.document_id,request.count),export)
@router.post('/quiz')
def quiz(request:QuizRequest,export:ExportRequest|None=None): return response(invoke(generate_quiz,request.document_id,request.count,request.difficulty),export)
@router.post('/questions')
def questions(request:QuestionsRequest): return invoke(generate_questions,request.document_id,request.question_type,request.count).model_dump()
