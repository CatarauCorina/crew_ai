import json, re
from typing import TypedDict, Dict, Any, List, Optional
from datetime import datetime, timedelta

from langgraph.graph import StateGraph, END
from base_agent import BaseAgent
from mongo_interface import MongoInterface

# Reuse only what we need; no duplicated helpers


class FinderState(TypedDict, total=False):
    topic: str
    company: str
    section_name: str
    section_notes: str
    want_document: bool
    lookback_days: int
    top_k: int
    max_loops: int
    loops_run: int
    finder_request: Optional[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    needs_more: bool
    diagnostics: Dict[str, Any]

    allow_placeholders: bool          # True when we’re only templating (no fresh Excel yet)
    placeholders: List[Dict[str, Any]]# [{"name":"H1 Revenue","token":"[H1_REVENUE]","hint":"SAR m"}]
    editor_guidance: str              # short instructions for the SectionEditor


class SectionState(TypedDict, total=False):
    # inputs
    topic: str
    company: str
    section_name: str             # e.g., "Financial Performance", "Dek", "Headline"
    section_notes: str            # brief instruction for this section
    tone: str                     # from style graph (optional)
    phrase_bank: List[str]        # from style graph (optional)
    boilerplate: str              # from style graph (optional)
    allow_placeholders: bool      # True in template mode
    evidence: List[Dict[str, Any]]# from finder: [{text, press_url/doc_url, press_title, ref, source_kind, ...}]
    max_revisions: int            # loop guard, e.g., 2
    section_memory: Dict[str, Dict[str, Any]]  # global memory of accepted sections so far

    # optional guidance from EvidenceApprover
    placeholders: List[Dict[str, Any]]         # [{"name":"H1 Revenue","token":"[H1_REVENUE]","hint":"SAR m"}]
    editor_guidance: str

    # outputs (creator)
    draft_md: str
    used_refs: List[str]           # ["#1","#3"]
    creator_warnings: List[str]

    # evaluator outputs
    accepted: bool
    reasons: List[str]
    needs_revision: bool
    revision_instructions: List[str]
    ask_finder_keywords: List[str] # if evaluator believes more evidence needed upstream

    # final (when accepted)
    final_md: str
    citations: List[Dict[str, Any]] # [{"ref":"#1","press_title":"...", "press_url":"...", "doc_url":"..."}]

    
class StyleState(TypedDict, total=False):
    topic: str
    client_id: str
    want_document: bool          
    max_docs: int                 
    lookback_days: int           

    type_label: str
    type_bucket: str
    type_confidence: float
    type_rationale: str

    # Step 2 discovery outputs
    discovered_sections: List[Dict[str, Any]]  # {name, aliases, prevalence, examples}
    structure: Dict[str, Any]                  # final template (sections/tone/phrases/boilerplate)
    html_wireframe: str                        # HTML skeleton
    doc_outline_md: str                        # Markdown outline for doc flow
    exemplars_used: List[str]                  # PR ids examined

