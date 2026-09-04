from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
class Summary(BaseModel): title:str; overview:str; key_points:list[str]=Field(default_factory=list); important_terms:list[str]=Field(default_factory=list); conclusion:str=""
class NoteSection(BaseModel): heading:str; explanation:str; key_points:list[str]=Field(default_factory=list); examples:list[str]=Field(default_factory=list)
class Notes(BaseModel): title:str; sections:list[NoteSection]=Field(default_factory=list)
class Flashcard(BaseModel): question:str; answer:str
class Flashcards(BaseModel):
 cards:list[Flashcard]=Field(default_factory=list)
 @model_validator(mode='after')
 def unique_cards(self):
  if len({x.question.strip().casefold() for x in self.cards}) != len(self.cards): raise ValueError('Duplicate flashcard questions')
  return self
class QuizQuestion(BaseModel):
 question:str; options:list[str]=Field(min_length=4,max_length=4); answer:str; explanation:str; topic:str=""; difficulty:str="medium"
 @model_validator(mode='after')
 def valid_answer(self):
  if self.answer.strip() not in [x.strip() for x in self.options]: raise ValueError('Quiz answer must be one of the options')
  return self
class Quiz(BaseModel):
 questions:list[QuizQuestion]=Field(default_factory=list)
 @model_validator(mode='after')
 def unique_questions(self):
  if len({x.question.strip().casefold() for x in self.questions}) != len(self.questions): raise ValueError('Duplicate quiz questions')
  return self
class StudyQuestion(BaseModel): question:str; type:str='short_answer'; difficulty:str='medium'; topic:str=''
class Questions(BaseModel): questions:list[StudyQuestion]=Field(default_factory=list)
class TopicUnit(BaseModel): title:str; topics:list[str]=Field(default_factory=list); subtopics:list[str]=Field(default_factory=list)
class Topics(BaseModel): major_topics:list[str]=Field(default_factory=list); concepts:list[str]=Field(default_factory=list); units:list[TopicUnit]=Field(default_factory=list)
class StudyGuide(BaseModel):
 title:str; learning_objectives:list[str]=Field(default_factory=list); prerequisites:list[str]=Field(default_factory=list); important_topics:list[str]=Field(default_factory=list); topic_dependencies:list[str]=Field(default_factory=list); revision_order:list[str]=Field(default_factory=list); key_concepts:list[str]=Field(default_factory=list); common_mistakes:list[str]=Field(default_factory=list); final_revision_checklist:list[str]=Field(default_factory=list)
