#!/usr/bin/env python3
import os, json, time, re
from collections import Counter
from pymongo import MongoClient
from openai import OpenAI

BUCKETS = [
    "Financial & Capital",
    "Deals & Corporate Actions",
    "Operations, Products & Projects",
    "Governance & People",
    "Regulatory, Compliance & Legal",
    "ESG, Sustainability & Community",
]

SYSTEM = (
    "You are a careful classifier for corporate press releases. "
    "Given TITLE and SUBTITLE, produce:\n"
    "1) a concise freeform type label (1–3 words), and\n"
    "2) ONE bucket chosen strictly from the allowed buckets.\n"
    "If uncertain about the label, still pick the best bucket.\n"
    "Return ONLY JSON."
)

USER_TMPL = """TITLE: {title}
SUBTITLE: {subtitle}

Allowed buckets (choose exactly one):
- Financial & Capital
- Deals & Corporate Actions
- Operations, Products & Projects
- Governance & People
- Regulatory, Compliance & Legal
- ESG, Sustainability & Community

Return ONLY JSON:
{{
  "type": "<concise label (1-3 words)>",
  "bucket": "<one of the allowed buckets exactly>",
  "confidence": 0.0-1.0,
  "rationale": "brief reason"
}}"""

def normalize_label(s: str) -> str:
    s = " ".join((s or "").strip().split())
    if not s:
        return "Other"
    words = s.split()
    s = " ".join(words[:3])[:80]
    return s.title()

def tagify(prefix: str, label: str) -> str:
    safe = re.sub(r"[:/|]+", "-", label)
    safe = re.sub(r"\s+", " ", safe).strip()
    return f"{prefix}:{safe}"

def main():
    mongo_uri = os.environ["MONGO_URI"]
    db_name   = os.getenv("DB_NAME", "SISCO")
    force     = os.getenv("FORCE", "0") == "1"
    pace_s    = float(os.getenv("PACE_SECONDS", "0.2"))

    db = MongoClient(mongo_uri)[db_name]
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    cur = db.PressRelease.find(
        {}, {"_id":1, "Name":1, "Subtitle":1, "Tags":1, "Type":1, "TypeBucket":1}
    ).sort("CreatedAt",-1)

    updated = 0
    bucket_counter = Counter()

    for pr in cur:
        if pr.get("Type") and pr.get("TypeBucket") and not force:
            continue

        title = (pr.get("Name") or "").strip()
        subtitle = (pr.get("Subtitle") or "").strip()
        if not title and not subtitle:
            continue

        msg = USER_TMPL.format(title=title, subtitle=subtitle)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": msg},
            ],
        )

        try:
            data = json.loads(resp.choices[0].message.content)
        except Exception:
            data = {"type": "Other", "bucket": None, "confidence": 0.0, "rationale": "parse_error"}

        typ = normalize_label(data.get("type", "Other"))
        bucket = (data.get("bucket") or "").strip()
        if bucket not in BUCKETS:
            # fall back to a reasonable default bucket if the model strays
            bucket = "Operations, Products & Projects"
        try:
            conf = float(data.get("confidence", 0.0))
        except Exception:
            conf = 0.0
        rationale = (data.get("rationale") or "").strip()

        tags = set(pr.get("Tags", []))
        if typ != "Other":
            tags.add(tagify("Event", typ))
        tags.add(tagify("Bucket", bucket))

        db.PressRelease.update_one(
            {"_id": pr["_id"]},
            {"$set": {
                "Type": typ,
                "TypeBucket": bucket,
                "TypeConfidence": conf,
                "TypeRationale": rationale,
                "Tags": sorted(tags),
            }}
        )

        bucket_counter[bucket] += 1
        updated += 1
        print(f"[{updated}] {title[:90]} → {typ} | {bucket} ({conf:.2f})")
        time.sleep(pace_s)

    print(f"\nDone. Labeled {updated} item(s).")
    if updated:
        print("Bucket distribution:")
        for b, c in bucket_counter.most_common():
            print(f"  - {b}: {c}")

if __name__ == "__main__":
    main()
