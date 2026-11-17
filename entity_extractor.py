# entities_extractor.py
from __future__ import annotations
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from bs4 import BeautifulSoup
from openai import OpenAI

from mongo_interface import MongoInterface

ALLOWED_TYPES = {"Company", "Asset", "Event", "Location", "Date", "KPI", "Person"}

SYSTEM_PROMPT = (
    "Extract entities from the text. Allowed types: Company, Asset, Event, Location, Date, KPI, Person. "
    "Return ONLY a JSON array. Each item:\n"
    '{"type":"Company|Asset|Event|Location|Date|KPI|Person",'
    '"value":"string","confidence":0.0-1.0,'
    '"attributes":{... optional ...},'
    '"excerpt":"short supporting quote"}'
)

class EntityExtractor:
    """
    Minimal LLM-based extractor with guardrails:
      - Uses TemplateHTML (clean) for PRs, ProcessedContent chunks for PDFs
      - Enforces type whitelist, min confidence, evidence-in-text
      - Canonicalizes Company to Companies collection (exact case-insensitive)
      - Idempotent (skip if already extracted unless force=True)
      - Updates PressRelease.Tags (Company/Event/Location/Date)
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        min_confidence: float = 0.6,
        require_evidence: bool = True,
        allowed_events: Optional[List[str]] = None,
    ):
        self.mi = MongoInterface()
        self.client = OpenAI()
        openai_key = os.environ["OPENAI_API_KEY"]
 
        self.openai_client = OpenAI(api_key=openai_key)
        self.model = model
        self.min_confidence = float(min_confidence)
        self.require_evidence = require_evidence
        self.allowed_events = set(allowed_events or [])

    # ---------- public API ----------

    def run(self, limit: Optional[int] = None, force: bool = False, include_pdfs: bool = True) -> int:
        """
        Process latest press releases. If `force=False`, skip PRs/docs that already have entities.
        Returns number of PRs processed (not entity count).
        """
        cur = self.mi.db.PressRelease.find({}, {"_id": 1, "TemplateHTML": 1}).sort("CreatedAt", -1)
        if limit:
            cur = cur.limit(limit)

        processed = 0
        for pr in cur:
            pr_id: ObjectId = pr["_id"]

            # 1) PR entities
            if force or not self._has_entities(pr_id):
                pr_text = self._html_to_text(pr.get("TemplateHTML") or "") or self._chunks_text(pr_id)
                ents = self._extract_and_filter(pr_text)
                if ents:
                    self._insert_entities(doc_id=pr_id, doc_kind="press", ents=ents)

            # 2) PDFs
            if include_pdfs:
                for doc in self.mi.db.Document.find({"PressReleaseId": pr_id}, {"_id": 1}):
                    doc_id = doc["_id"]
                    if force or not self._has_entities(doc_id):
                        pdf_text = self._chunks_text(doc_id)
                        pdf_ents = self._extract_and_filter(pdf_text)
                        if pdf_ents:
                            self._insert_entities(doc_id=doc_id, doc_kind="pdf", ents=pdf_ents)

            # 3) Update PR tags
            self._update_pr_tags(pr_id)
            processed += 1

        return processed

    def run_for_ids(self, press_release_ids: List[str], force: bool = False, include_pdfs: bool = True) -> int:
        processed = 0
        for pr_id_str in press_release_ids:
            pr_id = ObjectId(pr_id_str)
            pr = self.mi.db.PressRelease.find_one({"_id": pr_id}, {"TemplateHTML": 1})
            if not pr:
                continue

            if force or not self._has_entities(pr_id):
                pr_text = self._html_to_text(pr.get("TemplateHTML") or "") or self._chunks_text(pr_id)
                ents = self._extract_and_filter(pr_text)
                if ents:
                    self._insert_entities(pr_id, "press", ents)

            if include_pdfs:
                for doc in self.mi.db.Document.find({"PressReleaseId": pr_id}, {"_id": 1}):
                    doc_id = doc["_id"]
                    if force or not self._has_entities(doc_id):
                        pdf_text = self._chunks_text(doc_id)
                        pdf_ents = self._extract_and_filter(pdf_text)
                        if pdf_ents:
                            self._insert_entities(doc_id, "pdf", pdf_ents)

            self._update_pr_tags(pr_id)
            processed += 1
        return processed

    # ---------- internals ----------

    def _extract_and_filter(self, text: str) -> List[Dict[str, Any]]:
        """Call LLM → parse JSON → guardrails (type, confidence, evidence, event allowlist) → de-dup."""
        if not text or not text.strip():
            return []
        raw = self._llm_extract(text)
        if not raw:
            return []

        out: List[Dict[str, Any]] = []
        seen = set()
        t_lower = text.lower()
        for e in raw:
            et = (e.get("type") or "").strip()
            val = (e.get("value") or "").strip()
            conf = float(e.get("confidence", 0.9))
            if et not in ALLOWED_TYPES or not val:
                continue
            if conf < self.min_confidence:
                continue
            if et == "Event" and self.allowed_events and val not in self.allowed_events:
                continue
            if self.require_evidence:
                v = val.lower()
                excerpt = (e.get("excerpt") or "").lower()
                if v not in t_lower and v not in excerpt:
                    continue
            key = (et, val.lower())
            if key in seen:
                continue
            seen.add(key)

            # Canonicalize Company → Companies collection id (exact case-insensitive match)
            canonical_id = None
            if et == "Company":
                canonical_id = self._company_canonical_id(val)

            out.append({
                "type": et,
                "value": val,
                "confidence": conf,
                "attributes": e.get("attributes", {}),
                "excerpt": (e.get("excerpt") or "")[:400],
                "canonical_id": canonical_id,
            })
        return out

    def _llm_extract(self, text: str) -> List[Dict[str, Any]]:
        """Call the LLM and return parsed JSON list of entities (best-effort)."""
        prompt = f"{SYSTEM_PROMPT}\n\nText:\n```\n{text[:8000]}\n```"
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": "You are an information extraction assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        try:
            resp_value = resp.choices[0].message.content
            resp_value = resp_value.replace("json","")
            resp_value = resp_value.replace("`","")
            data = json.loads(resp_value)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _insert_entities(self, doc_id: ObjectId, doc_kind: str, ents: List[Dict[str, Any]]) -> None:
        rows = []
        for e in ents:
            rows.append({
                "DocId": doc_id,
                "DocKind": doc_kind,                               # "press" | "pdf"
                "Type": e["type"],
                "Value": e["value"],
                "CanonicalId": e.get("canonical_id"),
                "Attributes": e.get("attributes", {}),
                "Confidence": float(e.get("confidence", 0.9)),
                "Excerpt": e.get("excerpt", ""),
                "CreatedAt": datetime.utcnow(),
            })
        if rows:
            self.mi.db.Entities.insert_many(rows)

    def _update_pr_tags(self, pr_id: ObjectId) -> None:
        q = {"DocId": pr_id, "Type": {"$in": ["Company", "Event", "Location", "Date"]}}
        tags = [f"{e['Type']}:{e['Value']}" for e in self.mi.db.Entities.find(q, {"Type": 1, "Value": 1})]
        if tags:
            self.mi.db.PressRelease.update_one({"_id": pr_id}, {"$set": {"Tags": sorted(set(tags))}})

    def _has_entities(self, doc_id: ObjectId) -> bool:
        return self.mi.db.Entities.count_documents({"DocId": doc_id}) > 0

    def _chunks_text(self, doc_or_pr_id: ObjectId) -> str:
        chunks = self.mi.get_chunks_for_document(str(doc_or_pr_id))
        if not chunks:
            return ""
        return "\n".join(c.get("Content", "") for c in chunks)[:8000]

    @staticmethod
    def _html_to_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text("\n", strip=True)

    def _company_canonical_id(self, name: str) -> Optional[ObjectId]:
        if not name:
            return None
        # exact case-insensitive match on Parent/Child
        rec = self.mi.db.Companies.find_one(
            {"$or": [{"Parent": {"$regex": f"^{name}$", "$options": "i"}},
                     {"Child":  {"$regex": f"^{name}$", "$options": "i"}}]},
            {"_id": 1}
        )
        return rec["_id"] if rec else None


if __name__ == "__main__":
    # Optionally constrain Event values you accept:
    allowed_events = ["Interim Financial Results", "Acquisition", "Partnership", "Dividend", "Incorporation"]
    ex = EntityExtractor(model="gpt-4o-mini", min_confidence=0.6, require_evidence=True, allowed_events=allowed_events)
    processed = ex.run(limit=50, force=False, include_pdfs=True)
    print(f"Processed PRs: {processed}")