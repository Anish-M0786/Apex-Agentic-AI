"""Content Planner — determines scope, depth, and section outline before generation.

This module is responsible for understanding WHAT needs to be generated and HOW
deep it should be.  The artifact generators are never responsible for inventing
missing content — that is this module's job.

Architecture:
    User request
        → ContentPlanner.plan()          ← scope + depth + outline
            → content/service.py         ← generate each section with full context
                → Artifact generator     ← render only
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Task types
# ---------------------------------------------------------------------------

TASK_STUDY_NOTES = 'study_notes'
TASK_TECHNICAL_REPORT = 'technical_report'
TASK_BUSINESS_REPORT = 'business_report'
TASK_TUTORIAL = 'tutorial'
TASK_PRESENTATION = 'presentation'
TASK_PROGRAMMING = 'programming'
TASK_SUMMARY = 'summary'
TASK_GENERAL = 'general'


# ---------------------------------------------------------------------------
# Depth levels
# ---------------------------------------------------------------------------

DEPTH_QUICK = 'quick'        # "give me a quick summary"
DEPTH_STANDARD = 'standard'  # default
DEPTH_COMPREHENSIVE = 'comprehensive'  # "detailed", "comprehensive", "thorough"


# ---------------------------------------------------------------------------
# Broad topic registry — used to force comprehensive depth
# ---------------------------------------------------------------------------

_BROAD_TOPICS: list[str] = [
    'operating systems', 'operating system',
    'computer networks', 'computer network', 'networking',
    'machine learning', 'deep learning',
    'generative ai', 'artificial intelligence', 'ai',
    'database', 'dbms', 'database management',
    'cybersecurity', 'security', 'information security',
    'cloud computing', 'cloud',
    'data structures', 'algorithms', 'dsa',
    'computer architecture', 'computer organization',
    'software engineering', 'software development',
    'web development', 'full stack',
    'compiler design', 'theory of computation',
    'digital electronics', 'microprocessors',
    'distributed systems', 'parallel computing',
    'natural language processing', 'nlp',
    'computer vision', 'image processing',
]


def _is_broad_topic(topic: str) -> bool:
    t = topic.lower()
    return any(broad in t for broad in _BROAD_TOPICS)


# ---------------------------------------------------------------------------
# Depth detection
# ---------------------------------------------------------------------------

_QUICK_SIGNALS = {'quick', 'brief', 'short', 'concise', 'summary', 'overview', 'tldr', 'tl;dr'}
_DEEP_SIGNALS = {
    'detailed', 'detail', 'comprehensive', 'thorough', 'complete', 'in-depth',
    'in depth', 'extensive', 'full', 'deep', 'study notes', 'study guide',
    'everything', 'all topics', 'all chapters', 'semester', 'exam preparation',
}


def detect_depth(request: str, topic: str) -> str:
    text = request.lower()
    if any(sig in text for sig in _QUICK_SIGNALS):
        return DEPTH_QUICK
    if any(sig in text for sig in _DEEP_SIGNALS) or _is_broad_topic(topic):
        return DEPTH_COMPREHENSIVE
    return DEPTH_STANDARD


# ---------------------------------------------------------------------------
# Task type detection
# ---------------------------------------------------------------------------

def detect_task_type(request: str) -> str:
    text = request.lower()
    if any(w in text for w in ('study notes', 'study guide', 'revision notes', 'exam notes', 'lecture notes')):
        return TASK_STUDY_NOTES
    if any(w in text for w in ('tutorial', 'how to', 'step by step', 'step-by-step', 'guide me')):
        return TASK_TUTORIAL
    if any(w in text for w in ('business report', 'market', 'executive summary', 'business case')):
        return TASK_BUSINESS_REPORT
    if any(w in text for w in ('technical report', 'research report', 'technical document')):
        return TASK_TECHNICAL_REPORT
    if any(w in text for w in ('presentation', 'ppt', 'powerpoint', 'slides')):
        return TASK_PRESENTATION
    if any(w in text for w in ('code', 'implement', 'algorithm', 'function', 'program', 'write a', 'solve')):
        return TASK_PROGRAMMING
    if any(w in text for w in ('summary', 'summarize', 'brief', 'overview')):
        return TASK_SUMMARY
    return TASK_GENERAL


# ---------------------------------------------------------------------------
# Slide count detection
# ---------------------------------------------------------------------------

def detect_slide_count(request: str, depth: str) -> int:
    """Return the number of slides to generate."""
    # Explicit number in request
    m = re.search(r'(\d+)\s*(?:-\s*slide|slide)', request.lower())
    if m:
        return max(3, min(30, int(m.group(1))))
    # Depth-based defaults
    if depth == DEPTH_QUICK:
        return 6
    if depth == DEPTH_COMPREHENSIVE:
        return 12
    return 8


# ---------------------------------------------------------------------------
# Section count detection
# ---------------------------------------------------------------------------

def detect_section_count(depth: str, task_type: str) -> int:
    """Return the minimum number of sections a document should have."""
    if depth == DEPTH_QUICK:
        return 3
    if depth == DEPTH_COMPREHENSIVE:
        if task_type == TASK_STUDY_NOTES:
            return 10
        return 7
    # standard
    if task_type == TASK_STUDY_NOTES:
        return 6
    return 4


# ---------------------------------------------------------------------------
# Content plan dataclass
# ---------------------------------------------------------------------------

@dataclass
class ContentPlan:
    topic: str
    task_type: str
    depth: str
    audience: str
    purpose: str
    min_sections: int
    slide_count: int
    include_code: bool
    include_examples: bool
    include_exam_notes: bool
    format_hints: list[str] = field(default_factory=list)

    def depth_instruction(self) -> str:
        if self.depth == DEPTH_QUICK:
            return 'Be concise. Cover the most important points only.'
        if self.depth == DEPTH_COMPREHENSIVE:
            return (
                'Be thorough and comprehensive. Cover ALL major aspects of the topic. '
                'Each section must contain meaningful paragraphs with real explanations, '
                'not just bullet lists. Include definitions, how it works, why it matters, '
                'and concrete examples.'
            )
        return (
            'Provide good coverage of the topic. Each section should contain substantive '
            'explanations with examples where appropriate.'
        )

    def structure_instruction(self) -> str:
        """Return structure hints based on task type."""
        if self.task_type == TASK_STUDY_NOTES:
            return (
                'Structure as study notes: definitions, concept explanations, how it works, '
                'key properties, examples, comparisons (if applicable), and exam-relevant points.'
            )
        if self.task_type == TASK_TUTORIAL:
            return (
                'Structure as a tutorial: prerequisites, concept introduction, '
                'step-by-step explanation, worked examples, common mistakes, and a summary.'
            )
        if self.task_type == TASK_TECHNICAL_REPORT:
            return (
                'Structure as a technical report: abstract, introduction, background, '
                'methodology, detailed findings, implementation details, limitations, conclusion.'
            )
        if self.task_type == TASK_BUSINESS_REPORT:
            return (
                'Structure as a business report: executive summary, problem statement, '
                'context/market, analysis, findings, recommendations, risks, conclusion.'
            )
        if self.task_type == TASK_PROGRAMMING:
            return (
                'Cover: problem statement, concept explanation, when to use it, key intuition, '
                'algorithm/approach, step-by-step walkthrough, actual working code, '
                'example with dry run, time/space complexity, edge cases, common mistakes.'
            )
        return (
            'Structure logically with introduction, core concepts, detailed sections, '
            'examples, and conclusion.'
        )


def plan(
    topic: str,
    request: str,
    purpose: str = 'educational reference',
    audience: str = 'general readers',
) -> ContentPlan:
    """Create a content plan from a user request and topic."""
    task_type = detect_task_type(request)
    depth = detect_depth(request, topic)
    min_sections = detect_section_count(depth, task_type)
    slide_count = detect_slide_count(request, depth)

    text = request.lower()
    include_code = task_type == TASK_PROGRAMMING or any(
        w in text for w in ('code', 'implementation', 'c++', 'python', 'java', 'algorithm', 'program')
    )
    include_examples = depth != DEPTH_QUICK
    include_exam_notes = task_type == TASK_STUDY_NOTES or any(
        w in text for w in ('exam', 'interview', 'viva', 'test', 'revision')
    )

    return ContentPlan(
        topic=topic,
        task_type=task_type,
        depth=depth,
        audience=audience,
        purpose=purpose,
        min_sections=min_sections,
        slide_count=slide_count,
        include_code=include_code,
        include_examples=include_examples,
        include_exam_notes=include_exam_notes,
    )
