# content_finder_graph.py
from __future__ import annotations
import json, re, os
from typing import TypedDict, Dict, Any, List, Optional
from datetime import datetime, timedelta


from langgraph.graph import StateGraph, END
from base_agent import BaseAgent
from mongo_interface import MongoInterface

# Reuse only what we need; no duplicated helpers
from structure import _html_to_text, build_style_graph
from states import FinderState, SectionState, StyleState
from config_loader import get_config

# ---------- Helpers ----------
def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _build_query(company: str, topic: str, name: str, notes: str, finder_request: Optional[Dict[str, Any]]) -> str:
    config = get_config()
    section_terms = config.get_section_terms()
    
    terms: List[str] = [company or "", name or "", notes or "", topic or ""]
    if finder_request and isinstance(finder_request.get("add_keywords"), list):
        terms.extend([str(x) for x in finder_request["add_keywords"] if isinstance(x, (str, int, float))])
    
    n = (name or "").lower()
    
    # Use configuration-based terms
    if any(k in n for k in ["financial", "performance", "results"]):
        terms += section_terms.get('financial', [])
    elif any(k in n for k in ["operational", "operations", "highlight"]):
        terms += section_terms.get('operational', [])
    elif "outlook" in n or "strategy" in n:
        terms += section_terms.get('outlook_strategy', [])
    elif "company" in n or "about" in n or "information" in n or "boilerplate" in n:
        terms += section_terms.get('company_info', [])
    elif "contact" in n:
        terms += section_terms.get('contact', [])
    elif "quote" in n:
        terms += section_terms.get('quote', [])
    elif "headline" in n or "title" in n:
        terms += section_terms.get('headline', [])
    elif "dek" in n or "summary" in n:
        terms += section_terms.get('dek_summary', [])
    
    # Always include company-specific terms for better evidence retrieval
    terms += section_terms.get('company_specific', [])
    
    return _normalize(" ".join(terms))

def _recent_press_ids(mi: MongoInterface, lookback_days: int, k_docs: int) -> tuple[list, dict]:
    """Return IDs of most-recent PRs + map to CreatedAt for recency sorting."""
    since = datetime.utcnow() - timedelta(days=lookback_days)
    cur = mi.db.PressRelease.find(
        {"CreatedAt": {"$gte": since}},
        {"_id": 1, "CreatedAt": 1}
    ).sort("CreatedAt", -1).limit(k_docs)
    ids, created_map = [], {}
    for r in cur:
        ids.append(r["_id"])
        created_map[r["_id"]] = r["CreatedAt"]
    return ids, created_map

def _recent_doc_ids_for_prs(mi: MongoInterface, pr_ids: list) -> set:
    if not pr_ids:
        return set()
    docs = mi.db.Document.find({"PressReleaseId": {"$in": pr_ids}}, {"_id": 1})
    return {d["_id"] for d in docs}

# ---------- Agent 1: Content Finder ----------
class SectionCreatorAgent(BaseAgent):
    """
    Writes a Markdown draft for one section using ONLY the provided evidence.
    No section-specific style hints. Tone and notes are the only guidance.
    If allow_placeholders=True, it may insert provided placeholder tokens.
    """
    def __init__(self, model: str = None):
        super().__init__()
        config = get_config()
        model_config = config.get_model_config('section_creator')
        self.model = model or model_config['model']

    def run(self, state: SectionState) -> SectionState:
        sec = state["section_name"]
        notes = state.get("section_notes","")
        topic = state["topic"]
        company = state.get("company","SISCO")
        tone = state.get("tone","formal, factual, concise")
        phrases = state.get("phrase_bank", [])
        boiler = state.get("boilerplate","")
        placeholders = state.get("placeholders", [])
        allow_ph = bool(state.get("allow_placeholders", True))
        prior = state.get("section_memory", {})
        prior_names = list(prior.keys())

        revision_instructions = state.get("revision_instructions", [])
        editor_guidance = state.get("editor_guidance", "")
        previous_draft = state.get("draft_md", "")  

        # Evidence payload (compact)
        ev = state.get("evidence", [])
        ev_brief = []
        for e in ev:
            ev_brief.append({
                "ref": e.get("ref"),
                "source_kind": e.get("source_kind"),
                "press_title": e.get("press_title"),
                "press_url": e.get("press_url"),
                "doc_url": e.get("doc_url"),
                "text": (e.get("text") or "")[:600]
            })


        config = get_config()
        system = config.get_prompt('section_creator', 'system_prompt')

        user_payload = {
            "TOPIC": topic,
            "COMPANY": company,
            "SECTION": sec,
            "NOTES": notes,
            "TONE": tone,
            "PHRASE_BANK": phrases[:12],
            "PLACEHOLDERS_ALLOWED": allow_ph,
            "PLACEHOLDERS": placeholders,   # [{"name","token","hint"}]
            "PREVIOUS_SECTIONS": [
                {"name": n, "snippet": (prior[n].get("text","")[:300] if isinstance(prior.get(n), dict) else "")}
                for n in prior_names
            ],
            "EVIDENCE": ev_brief,
            # NEW: revision context
            "PREVIOUS_DRAFT": previous_draft,
            "REVISION_INSTRUCTIONS": revision_instructions,
            "EDITOR_GUIDANCE": editor_guidance,
            # Enhanced style context
            "WRITING_STYLE_GUIDANCE": state.get("writing_style_guidance", ""),
            "STYLE_CONSISTENCY_NOTES": state.get("style_consistency_notes", ""),
        }

        prompt = config.get_prompt('section_creator', 'user_prompt')
        # system = (
        #     "You are a precise press-release section writer. "
        #     "Write only the requested SECTION in Markdown using the EVIDENCE provided. "
        #     "Do not invent facts. If figures are missing and placeholders are allowed, use the placeholder tokens. "
        #     "Keep the tone aligned with the provided tone. Avoid hype."
        # )

        # user_payload = {
        #     "TOPIC": topic,
        #     "COMPANY": company,
        #     "SECTION": sec,
        #     "NOTES": notes,
        #     "TONE": tone,
        #     "PHRASE_BANK": phrases[:12],
        #     "PLACEHOLDERS_ALLOWED": allow_ph,
        #     "PLACEHOLDERS": placeholders,   # [{"name","token","hint"}]
        #     "PREVIOUS_SECTIONS": [
        #         {"name": n, "snippet": (prior[n].get("text","")[:300] if isinstance(prior.get(n), dict) else "")}
        #         for n in prior_names
        #     ],
        #     "EVIDENCE": ev_brief
        # }

        # # No style hints; minimal guardrails only.
        # prompt = (
        #     "Return ONLY JSON with keys: draft_md, used_refs (array of ref ids), warnings (array).\n"
        #     "Rules:\n"
        #     "- Use only provided evidence (or placeholder tokens if allowed).\n"
        #     "- Keep content concise and factual; align with the provided tone and notes.\n"
        #     "- Do not add unrelated headers or extra sections.\n"
        # )

        model_config = config.get_model_config('section_creator')
        raw = self.llm_inference(
            messages=[
                {"role":"system","content":system},
                {"role":"user","content": json.dumps(user_payload, ensure_ascii=False)},
                {"role":"user","content": prompt}
            ],
            model=self.model, temperature=model_config['temperature']
        )
        try:
            data = json.loads(raw)
        except Exception:
            data = {"draft_md":"[data pending]","used_refs":[],"warnings":["parse_error"]}

        state["draft_md"] = (data.get("draft_md") or "").strip() or "[data pending]"
        state["used_refs"] = [r for r in data.get("used_refs",[]) if isinstance(r,str)]
        state["creator_warnings"] = [w for w in data.get("warnings",[]) if isinstance(w,str)]
        return state
    

class SectionFinalEvaluatorAgent(BaseAgent):
    """
    Evaluates a single-section draft for:
    - relevance to TOPIC and SECTION
    - evidence grounding (and placeholder discipline)
    - tone & style fit
    - cross-section redundancy/conflict (uses section_memory)
    Produces accept/revise decision with concrete revision instructions.
    """
    def __init__(self, model: str = None):
        super().__init__()
        config = get_config()
        model_config = config.get_model_config('section_evaluator')
        self.model = model or model_config['model']

    def run(self, state: SectionState) -> SectionState:
        sec = state["section_name"]
        topic = state["topic"]
        tone = state.get("tone","formal, factual, concise")
        allow_ph = bool(state.get("allow_placeholders", True))
        draft = state.get("draft_md","").strip()
        evidence = state.get("evidence", [])
        used_refs = state.get("used_refs", [])
        phrases = state.get("phrase_bank", [])
        prior = state.get("section_memory", {})

        ev_map = { (e.get("ref") or f"#{i+1}"): e for i,e in enumerate(evidence) }
        used_meta = []
        for r in used_refs:
            e = ev_map.get(r)
            if e:
                used_meta.append({
                    "ref": r,
                    "press_title": e.get("press_title"),
                    "press_url": e.get("press_url"),
                    "doc_url": e.get("doc_url"),
                    "source_kind": e.get("source_kind")
                })

        payload = {
            "TOPIC": topic,
            "SECTION": sec,
            "TONE": tone,
            "ALLOW_PLACEHOLDERS": allow_ph,
            "PHRASE_BANK": phrases[:10],
            "DRAFT": draft,
            "USED_REFS": used_refs,
            "EVIDENCE_SNIPPETS": [{ "ref": k, "text": (ev_map[k].get("text","")[:500] if k in ev_map else "") } for k in used_refs],
            "PREVIOUS_ACCEPTED_SECTIONS": [
                {"name": n, "snippet": (prior[n].get("text","")[:400] if isinstance(prior.get(n), dict) else "")} for n in prior.keys()
            ]
        }

        config = get_config()
        system = config.get_prompt('section_evaluator', 'system_prompt')
        schema = (
            "{\n"
            '  "accept": true/false,\n'
            '  "reasons": ["detailed explanation of acceptance or rejection"],\n'
            '  "needs_revision": true/false,\n'
            '  "revision_instructions": ["specific, actionable improvement suggestions"],\n'
            '  "ask_finder_keywords": ["only if fresh evidence is needed"],\n'
            '  "quality_score": 1-10,\n'
            '  "style_feedback": "specific feedback on writing style and phrase bank usage",\n'
            '  "content_feedback": "specific feedback on content depth and coverage",\n'
            '  "suggestions": ["additional improvement suggestions for better quality"]\n'
            "}"
        )
        user = f"""PAYLOAD:
{json.dumps(payload, ensure_ascii=False)}

EVALUATION GUIDELINES:
- If ALLOW_PLACEHOLDERS is true and the content uses appropriate placeholders, ACCEPT it
- Only ask for more evidence if content is completely off-topic or lacks basic structure
- Placeholders are acceptable when actual data is not available in the evidence
- Focus on content quality, writing style, and professional presentation
- Avoid infinite loops by accepting reasonable placeholder usage

Return ONLY JSON with this schema:
{schema}"""

        model_config = config.get_model_config('section_evaluator')
        raw = self.llm_inference(
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            model=self.model, temperature=model_config['temperature']
        )
        try:
            data = json.loads(raw)
        except Exception:
            data = {
                "accept": False,
                "reasons": ["parse_error"],
                "needs_revision": True,
                "revision_instructions": ["Rewrite with comprehensive coverage; ensure content draws from provided evidence or placeholders only."],
                "ask_finder_keywords": [],
                "quality_score": 3,
                "style_feedback": "Unable to evaluate due to parse error",
                "content_feedback": "Unable to evaluate due to parse error",
                "suggestions": ["Ensure proper JSON formatting in response"]
            }

        state["accepted"] = bool(data.get("accept"))
        state["reasons"] = [r for r in data.get("reasons",[]) if isinstance(r,str)]
        state["needs_revision"] = bool(data.get("needs_revision"))
        state["revision_instructions"] = [i for i in data.get("revision_instructions",[]) if isinstance(i,str)]
        state["ask_finder_keywords"] = [k for k in data.get("ask_finder_keywords",[]) if isinstance(k,str)]
        state["quality_score"] = data.get("quality_score", 5)
        state["style_feedback"] = data.get("style_feedback", "")
        state["content_feedback"] = data.get("content_feedback", "")
        state["suggestions"] = [s for s in data.get("suggestions",[]) if isinstance(s,str)]

        if state["accepted"]:
            state["final_md"] = draft
            # materialize citations for downstream (pandoc, etc.)
            state["citations"] = used_meta
        return state




class ContentFinderAgent(BaseAgent):
    """
    Retrieves evidence for ONE section using:
      - Atlas Search over PressRelease (with recency filter)
      - Atlas Search over ProcessedContent (PDF chunks), restricted to most-recent PR docs
      - Vector search over ProcessedContent (restricted to same doc set)
    Dedupes and sorts by recency first, then score.
    """
    def __init__(self):
        super().__init__()
        self.mi = MongoInterface()

    # Atlas text search on PRs, restricted to most-recent PR IDs
    def _atlas_search_press(self, query: str, recent_pr_ids: list, limit: int) -> List[Dict[str, Any]]:
        if not recent_pr_ids:
            return []
        pipeline = [
            {"$search": {"index": "default", "text": {"query": query, "path": {"wildcard": "*"}}}},
            {"$match": {"_id": {"$in": recent_pr_ids}}},
            {"$limit": max(1, limit)},
            {"$project": {"_id":1, "Name":1, "Subtitle":1, "Url":1, "TemplateHTML":1, "CreatedAt":1,
                          "score":{"$meta":"searchScore"}}}
        ]
        out = list(self.mi.db.PressRelease.aggregate(pipeline))
        for r in out:
            html = r.get("TemplateHTML") or ""
            r["text"] = (_html_to_text(html)[:2000] or " ".join(filter(None, [r.get("Name",""), r.get("Subtitle","")])))
            r["source_kind"] = "press"
            r["created_at"] = r.get("CreatedAt")
        return out

    # Atlas text search on ProcessedContent (PDF chunks), restricted to docs of recent PRs
    def _atlas_search_chunks(self, query: str, recent_doc_ids: set, limit: int) -> List[Dict[str, Any]]:
        if not recent_doc_ids:
            return []
        pipeline = [
            {"$search": {"index": "default", "text": {"query": query, "path": {"wildcard": "*"}}}},
            {"$match": {"DocumentId": {"$in": list(recent_doc_ids)}}},
            {"$limit": max(1, limit * 2)},  # oversample then trim
            {"$project": {"_id":1, "DocumentId":1, "Content":1, "score":{"$meta":"searchScore"}}}
        ]
        hits = list(self.mi.db.ProcessedContent.aggregate(pipeline))
        out = []
        for h in hits:
            doc = self.mi.db.Document.find_one({"_id": h["DocumentId"]}, {"Url":1, "PressReleaseId":1})
            pr  = self.mi.db.PressRelease.find_one({"_id": doc["PressReleaseId"]}, {"Url":1, "Name":1, "CreatedAt":1}) if doc and doc.get("PressReleaseId") else None
            out.append({
                "text": (h.get("Content","")[:1500]),
                "doc_url": (doc or {}).get("Url"),
                "press_url": (pr or {}).get("Url"),
                "press_title": (pr or {}).get("Name"),
                "score": float(h.get("score", 0)),
                "created_at": (pr or {}).get("CreatedAt"),
                "source_kind": "chunk",
            })
            if len(out) >= limit:
                break
        return out

    # Vector search on ProcessedContent (PDF chunks), restricted to doc whitelist
    def _vector_search_chunks(self, query: str, whitelist_doc_ids: list, limit: int) -> List[Dict[str, Any]]:
        out = []
        try:
            # Prefer filtered vector search if available in your interface
            hits = self.mi.vector_search_filtered(query, [str(x) for x in whitelist_doc_ids], limit=limit)
        except Exception:
            # fallback: unfiltered, then client-side filter
            hits = self.mi.similarity_search(query, limit=limit*2)
        for h in hits:
            doc_id = h.get("DocumentId")
            if whitelist_doc_ids and doc_id not in whitelist_doc_ids:
                continue
            doc = self.mi.db.Document.find_one({"_id": doc_id}, {"Url":1, "PressReleaseId":1})
            pr  = self.mi.db.PressRelease.find_one({"_id": doc["PressReleaseId"]}, {"Url":1, "Name":1, "CreatedAt":1}) if doc and doc.get("PressReleaseId") else None
            out.append({
                "text": h.get("Content","")[:1500],
                "doc_url": (doc or {}).get("Url"),
                "press_url": (pr or {}).get("Url"),
                "press_title": (pr or {}).get("Name"),
                "score": float(h.get("score", 0)),
                "created_at": (pr or {}).get("CreatedAt"),
                "source_kind": "chunk_vec",
            })
            if len(out) >= limit:
                break
        return out

    def run(self, state: FinderState) -> FinderState:
        company = state["company"]
        topic   = state["topic"]
        name    = state["section_name"]
        notes   = state.get("section_notes", "")
        want_doc= bool(state.get("want_document", False))
        top_k   = int(state.get("top_k", 6))
        lookback= int(state.get("lookback_days", 540))

        # 1) build recency scope first
        recent_pr_ids, pr_created_map = _recent_press_ids(self.mi, lookback, k_docs=max(10, top_k*2))
        recent_doc_ids = _recent_doc_ids_for_prs(self.mi, recent_pr_ids)

        # 2) build query
        query = _build_query(company, topic, name, notes, state.get("finder_request"))

        # 3) searches
        press_hits   = self._atlas_search_press(query, recent_pr_ids, limit=max(1, top_k//2))
        chunk_hits_t = self._atlas_search_chunks(query, recent_doc_ids, limit=max(1, top_k)) if want_doc else []
        chunk_hits_v = self._vector_search_chunks(query, list(recent_doc_ids), limit=max(1, top_k)) if want_doc else []

        combined = press_hits + chunk_hits_t + chunk_hits_v

        # 4) dedupe + recency-first ordering
        seen, evidence = set(), []
        def _key(ev): return _normalize(ev.get("text",""))[:220]
        def _rec(ev): 
            ts = ev.get("created_at")
            return ts if isinstance(ts, datetime) else datetime.min
        for ev in sorted(combined, key=lambda r: (_rec(r), float(r.get("score", 0))), reverse=True):
            k = _key(ev)
            if k and k not in seen:
                seen.add(k); evidence.append(ev)
            if len(evidence) >= top_k:
                break

        for i, ev in enumerate(evidence, 1):
            ev["ref"] = f"#{i}"

        state["evidence"] = evidence
        state["needs_more"] = False
        state["diagnostics"] = {
            "query": query,
            "press_hits": len(press_hits),
            "chunk_text_hits": len(chunk_hits_t),
            "chunk_vec_hits": len(chunk_hits_v),
            "recent_pr_ids": len(recent_pr_ids),
            "recent_doc_ids": len(recent_doc_ids),
        }
        state["loops_run"] = int(state.get("loops_run", 0))
        return state

# ---------- Agent 1.5: Evidence Approver (validator for finder) ----------
class EvidenceApproverAgent(BaseAgent):
    """
    Validates whether evidence is sufficient for the *current goal*:
      - If allow_placeholders=True: sufficient when structure/phrasing patterns are present,
        even without new numbers. Returns placeholder tokens + editor guidance.
      - If allow_placeholders=False: require factual content for the section; else request more.
    """
    def __init__(self, model: str = None):
        super().__init__()
        config = get_config()
        model_config = config.get_model_config('evidence_approver')
        self.model = model or model_config['model']

    def run(self, state: FinderState) -> FinderState:
        name   = state["section_name"]
        notes  = state.get("section_notes","")
        topic  = state["topic"]
        ev     = state.get("evidence", [])
        templ  = bool(state.get("allow_placeholders", True))

        snippets = [ _normalize(e.get("text",""))[:500] for e in ev ]
        ev_json  = json.dumps(snippets, ensure_ascii=False)

        config = get_config()
        system = config.get_prompt('evidence_approver', 'system_prompt')

        user_template = config.get_prompt('evidence_approver', 'user_prompt_template')
        user = user_template.format(
            topic=topic,
            name=name,
            notes=notes,
            allow_placeholders=str(templ).lower(),
            evidence_json=ev_json
        )

        model_config = config.get_model_config('evidence_approver')
        raw = self.llm_inference(
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            model=self.model,
            temperature=model_config['temperature']
        )
        try:
            data = json.loads(raw)
        except Exception:
            data = {
                "sufficient": bool(ev) if templ else False,
                "reason": "parse_error",
                "uses_placeholders": templ,
                "placeholders": [],
                "editor_guidance": "If numbers are missing, emit [data pending] tokens.",
                "suggested_keywords": []
            }

        sufficient = bool(data.get("sufficient"))
        uses_ph    = bool(data.get("uses_placeholders"))
        ph_list    = data.get("placeholders") or []
        guidance   = (data.get("editor_guidance") or "").strip()

        if sufficient:
            # Approve & pass guidance/placeholders to the editor stage
            state["needs_more"] = False
            state["placeholders"] = [
                p for p in ph_list
                if isinstance(p, dict) and p.get("token") and p.get("name")
            ]
            state["editor_guidance"] = guidance or (
                "Draft the section using concise bullets; insert placeholder tokens for any missing figures."
            )
            return state

        # Check if we've already tried too many times - if so, accept with placeholders
        loops_run = int(state.get("loops_run", 0))
        max_loops = int(state.get("max_loops", 3))
        
        if loops_run >= max_loops - 1:
            # We're at the limit, accept with placeholders to prevent getting stuck
            state["needs_more"] = False
            state["placeholders"] = [
                {"name": f"{name} Data", "token": f"[{name.upper().replace(' ', '_')}_DATA]", "hint": "data pending"}
            ]
            state["editor_guidance"] = f"Create {name} content using placeholder for missing data."
            state["diagnostics"] = {**state.get("diagnostics", {}), "approver_reason": f"Max loops reached ({max_loops}), using placeholders"}
            return state
        
        # Not sufficient → request another finder pass with extra keywords
        kws = [k for k in (data.get("suggested_keywords") or []) if isinstance(k, str) and k.strip()]
        if not kws:
            # fallback refinement
            if templ:
                kws = [name, "template phrasing", "structure", "boilerplate", "section headings"]
            else:
                kws = [name, "latest", "verified figures", "KPIs"]
        state["needs_more"] = True
        state["finder_request"] = {"add_keywords": kws}
        state["diagnostics"] = {**state.get("diagnostics", {}), "approver_reason": data.get("reason","")}
        return state


def build_section_creator_graph(model: str = None):
    config = get_config()
    creator = SectionCreatorAgent(model=model)
    evaluator = SectionFinalEvaluatorAgent(model=model)

    g = StateGraph(SectionState)
    g.add_node("create_section", lambda s: creator.run(s))
    g.add_node("evaluate_section", lambda s: evaluator.run(s))

    g.set_entry_point("create_section")
    g.add_edge("create_section", "evaluate_section")

    def route(state: SectionState):
        # If evaluator needs more evidence, stop here so outer orchestrator can call the finder again.
        if state.get("ask_finder_keywords"):
            return END
        # Loop creator if revisions requested and we still have budget
        curr = int(state.get("_rev_count", 0))
        max_revs = int(state.get("max_revisions", 2))
        if state.get("needs_revision") and curr < max_revs:
            state["_rev_count"] = curr + 1
            return "create_section"
        return END

    g.add_conditional_edges("evaluate_section", route, {"create_section":"create_section", END:END})
    return g.compile()



def build_finder_graph(model: str = "gpt-4o-mini"):
    finder  = ContentFinderAgent()
    approver= EvidenceApproverAgent(model=model)

    g = StateGraph(FinderState)
    g.add_node("find_content", lambda s: finder.run(s))
    g.add_node("approve_evidence", lambda s: approver.run(s))

    g.set_entry_point("find_content")
    g.add_edge("find_content", "approve_evidence")

    def route(state: FinderState):
        loops = int(state.get("loops_run", 0))
        max_loops = int(state.get("max_loops", 3))
        if state.get("needs_more") and loops < max_loops:
            state["loops_run"] = loops + 1
            return "find_content"
        return END

    g.add_conditional_edges("approve_evidence", route, {"find_content": "find_content", END: END})
    return g.compile()


# ---------- Integrated example run (style -> finder -> creator/evaluator) ----------
if __name__ == "__main__":
    TOPIC = "SISCO announces interim financial results for the six months ended 30 June 2025."
    COMPANY = "SISCO"

    # (A) Get structure from style graph (sections, tone, phrase_bank, boilerplate)
    style_app = build_style_graph()
    style_out: StyleState = style_app.invoke({
        "topic": TOPIC,
        "client_id": COMPANY,
        "want_document": True,
        "max_docs": 5,
        "lookback_days": 540,
    }, config={"recursion_limit": 10})
    structure = style_out.get("structure", {}) or {}
    sections = structure.get("sections", []) or []
    tone = structure.get("tone", "formal, factual, concise")
    phrase_bank = structure.get("phrase_bank", []) or []
    boilerplate = structure.get("boilerplate", "") or ""
    print(f"Discovered {len(sections)} sections from style graph.")

    # (B) Build graphs
    finder_app  = build_finder_graph()
    creator_app = build_section_creator_graph()

    # (C) Cross-section memory carried across sections
    section_memory: Dict[str, Dict[str, Any]] = {}

    # Collect outputs
    per_section_results: Dict[str, Any] = {}
    assembled_md_parts: List[str] = []

    for s in sections:
        sec_name  = (s.get("name") or "Section").strip()
        sec_notes = s.get("notes", "")

        # ---- Finder loop (recency + PR HTML + ProcessedContent + vector)
        fstate: FinderState = {
            "topic": TOPIC,
            "company": COMPANY,
            "section_name": sec_name,
            "section_notes": sec_notes,
            "want_document": True,     # include ProcessedContent
            "lookback_days": 540,
            "top_k": 6,
            "max_loops": 2,
            "allow_placeholders": True  # template mode: placeholders allowed
        }
        fout = finder_app.invoke(fstate)

        # Store finder diagnostics
        per_section_results[sec_name] = {
            "needs_more": fout.get("needs_more", False),
            "finder_request": fout.get("finder_request"),
            "diagnostics": fout.get("diagnostics", {}),
            "evidence": fout.get("evidence", []),
        }

        # ---- Creator/Evaluator loop for this section
        cstate: SectionState = {
            "topic": TOPIC,
            "company": COMPANY,
            "section_name": sec_name,
            "section_notes": sec_notes,
            "tone": tone,
            "phrase_bank": phrase_bank,
            "boilerplate": boilerplate,
            "allow_placeholders": True,  # until Excel numbers arrive
            "evidence": per_section_results[sec_name]["evidence"],
            "placeholders": fout.get("placeholders", []),       # from EvidenceApproverAgent
            "editor_guidance": fout.get("editor_guidance", ""), # from EvidenceApproverAgent
            "max_revisions": 2,
            "section_memory": section_memory,
            # Enhanced style context
            "writing_style_guidance": f"Use phrases from phrase bank naturally. Maintain {tone} tone throughout. Create comprehensive, detailed content.",
            "style_consistency_notes": "Ensure consistent use of phrase bank terms and maintain professional tone across all paragraphs."
        }

        cout = creator_app.invoke(cstate, config={"recursion_limit": 5})

        # If evaluator asked for more evidence, do one refinement pass via finder with suggested keywords
        if cout.get("ask_finder_keywords"):
            add_kw = cout.get("ask_finder_keywords") or []
            # re-run finder once with extra keywords
            fstate["finder_request"] = {"add_keywords": add_kw}
            fstate["loops_run"] = 0  # let the finder loop try again within its own limits
            fout2 = finder_app.invoke(fstate)

            # re-run creator with updated evidence
            cstate["evidence"] = fout2.get("evidence", [])
            cout = creator_app.invoke(cstate, config={"recursion_limit": 5})

        # Save final/accepted or draft result
        if cout.get("accepted"):
            final_md = cout.get("final_md", "").strip()
            section_memory[sec_name] = {"text": final_md, "citations": cout.get("citations", [])}
            per_section_results[sec_name]["final_md"] = final_md
            per_section_results[sec_name]["citations"] = cout.get("citations", [])
            assembled_md_parts.append(f"## {sec_name}\n\n{final_md}\n")
        else:
            # Keep last draft and instructions (useful for debugging)
            per_section_results[sec_name]["draft_md"] = cout.get("draft_md", "")
            per_section_results[sec_name]["needs_revision"] = cout.get("needs_revision", False)
            per_section_results[sec_name]["revision_instructions"] = cout.get("revision_instructions", [])
            assembled_md_parts.append(f"## {sec_name}\n\n{cout.get('draft_md','[data pending]')}\n")

        # Log a comprehensive progress line with enhanced feedback
        print(f"\n=== {sec_name} ===")
        print("accepted:", cout.get("accepted"), "| needs_revision:", cout.get("needs_revision"))
        print("quality_score:", cout.get("quality_score", "N/A"))
        
        if cout.get("style_feedback"):
            print("style_feedback:", cout["style_feedback"][:200] + "..." if len(cout["style_feedback"]) > 200 else cout["style_feedback"])
        
        if cout.get("content_feedback"):
            print("content_feedback:", cout["content_feedback"][:200] + "..." if len(cout["content_feedback"]) > 200 else cout["content_feedback"])
        
        if cout.get("ask_finder_keywords"):
            print("finder refinement keywords:", cout["ask_finder_keywords"])
        
        if cout.get("revision_instructions"):
            print("revision tips:", "; ".join(cout["revision_instructions"])[:240])
        
        if cout.get("suggestions"):
            print("suggestions:", "; ".join(cout["suggestions"])[:200])

    # (D) Final assembled Markdown (sections in discovered order)
    final_markdown = "\n".join(assembled_md_parts).strip()

    print("\n\n================= FINAL MARKDOWN (preview) =================\n")
    print(final_markdown)
    print("\n============================================================\n")
