from __future__ import annotations
import re
from backend.config import get_settings
from backend.code.models import SUPPORTED_LANGUAGES
def validate_code(code:str)->str:
 limit=getattr(get_settings(),'code_max_input_chars',30000)
 if not code or not code.strip(): raise ValueError('code must not be empty')
 if len(code)>limit: raise ValueError(f'code exceeds maximum of {limit} characters')
 return code
def validate_language(language:str|None,code:str='')->str:
 found=(language or detect_language(code)[0]).lower().replace('c++','cpp').replace('js','javascript').replace('ts','typescript')
 if found not in SUPPORTED_LANGUAGES: raise ValueError('Unsupported or ambiguous language')
 return found
def detect_language(code:str)->tuple[str,bool]:
 text=code.lower()
 clues=[('python',['def ','import ','print(']),('javascript',['console.log','function ','=>']),('typescript',['interface ','type ','const ']),('java',['public class','system.out']),('cpp',['#include','std::','using namespace']),('c',['#include','printf(','scanf(']),('sql',['select ',' from ','create table']),('html',['<html','<div','<!doctype']),('css',['{','color:','margin:']),('bash',['#!/bin/bash','echo ','fi\n'])]
 scores=[(lang,sum(x in text for x in marks)) for lang,marks in clues]; scores.sort(key=lambda x:x[1],reverse=True)
 return (scores[0][0] if scores and scores[0][1] else 'python', bool(scores and scores[0][1]>(scores[1][1] if len(scores)>1 else 0)))
