from __future__ import annotations
from pydantic import BaseModel,Field,field_validator
SUPPORTED_LANGUAGES={'python','c','cpp','java','javascript','typescript','sql','html','css','bash'}
class Complexity(BaseModel):
 time:str
 space:str
 reasoning:str=''
class GeneratedTestCase(BaseModel): name:str; code:str; purpose:str
class CodeGeneration(BaseModel): language:str; code:str; explanation:str; complexity:Complexity; test_cases:list[GeneratedTestCase]=Field(default_factory=list)
class ExplainCode(BaseModel): overview:str; steps:list[str]=Field(default_factory=list); important_concepts:list[str]=Field(default_factory=list); complexity:Complexity; potential_pitfalls:list[str]=Field(default_factory=list)
class CodeIssue(BaseModel):
 line:int|None=None
 description:str
 severity:str
 @field_validator('severity')
 @classmethod
 def severity_valid(cls,v):
  if v not in {'info','warning','error','critical'}: raise ValueError('Invalid severity')
  return v
class DebugResult(BaseModel): language:str; issues:list[CodeIssue]=Field(default_factory=list); fixed_code:str; explanation:str; analysis_mode:str='static analysis'
class RefactorResult(BaseModel): language:str; original_code:str; refactored_code:str; changes:list[str]=Field(default_factory=list); reasoning:str=''
class ReviewResult(BaseModel): summary:str; issues:list[CodeIssue]=Field(default_factory=list); strengths:list[str]=Field(default_factory=list); suggestions:list[str]=Field(default_factory=list)
class TestCase(BaseModel): name:str; code:str; purpose:str
class TestGeneration(BaseModel): language:str; test_framework:str; tests:list[TestCase]=Field(default_factory=list); note:str='Generated tests have not been executed.'
class Documentation(BaseModel): language:str; documentation:str; usage:str=''; parameters:list[str]=Field(default_factory=list); returns:str=''; assumptions:list[str]=Field(default_factory=list); limitations:list[str]=Field(default_factory=list)
class ComplexityAnalysis(BaseModel): worst_case:str; average_case:str|None=None; best_case:str|None=None; space:str; reasoning:str
