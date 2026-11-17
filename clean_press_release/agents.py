import os
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from pathlib import Path
import tempfile
from time import sleep

from mongo_interface import MongoInterface
from pdf_reader import PDFReader
from entity_extractor import extract_entities_node

from langchain.text_splitter import RecursiveCharacterTextSplitter
from selenium_scrapper import download_pdf_with_selenium_cookies

BASE_URL = "https://sisco.com.sa/en/media/press"
DETAIL_PATH_KEY = "/en/media/press/view/"
PAGE_STEP = 6  # pagination offset: /P6, /P12, etc.


PDF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

BROWSER_HEADERS = {
    "User-Agent": PDF_HEADERS["User-Agent"],
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(BROWSER_HEADERS)
    s.max_redirects = 5
    # Warm up on Saudiexchange to get BIG-IP / TS cookies
    try:
        s.get("https://www.saudiexchange.sa/", timeout=15)
        s.get("https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports", timeout=15)
    except Exception:
        pass
    return s

def robust_pdf_get(session: requests.Session, url: str, referer: str | None = None, timeout: int = 60) -> bytes:
    """
    Download a PDF with realistic headers + referer and cookie reuse.
    Retries with alternate referers on 403.
    """
    # candidates for Referer
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    directory = f"{base}{parsed.path.rsplit('/', 1)[0]}/"
    referers = [r for r in [referer, base, directory] if r]

    for attempt, ref in enumerate(referers or [base], start=1):
        hdrs = {**PDF_HEADERS, "Referer": ref}
        try:
            # no conditional headers
            resp = session.get(url, headers=hdrs, timeout=timeout, stream=True)
            if resp.status_code == 200 and "application/pdf" in resp.headers.get("Content-Type", "").lower():
                return resp.content
            if resp.status_code == 200:
                # Sometimes they send with octet-stream
                return resp.content
            if resp.status_code in (401, 403):
                # try next referer candidate
                sleep(0.5 * attempt)
                continue
            resp.raise_for_status()
            return resp.content
        except requests.HTTPError as e:
            if getattr(e.response, "status_code", None) in (401, 403) and attempt < 3:
                sleep(0.5 * attempt)
                continue
            raise

    # last try: re-warm cookies then retry once with base referer
    try:
        session.get(base, timeout=10)
        hdrs = {**PDF_HEADERS, "Referer": base}
        resp = session.get(url, headers=hdrs, timeout=timeout, stream=True)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        raise RuntimeError(f"Failed to fetch PDF (403/blocked): {url}") from e


class PressState(TypedDict):
    base_url: str
    releases: List[Dict[str, Any]]  # list of {url, text, metadata}
    _session: Any           



# ----------------- Helpers -----------------
def fetch_html(url: str, session: requests.Session) -> str:
    r = session.get(url, headers=BROWSER_HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

# def download_pdf(url: str, tmpdir: Path, session: requests.Session, referer: str | None = None) -> Path:
#     data = robust_pdf_get(session, url, referer=referer)
#     fp = tmpdir / Path(url).name
#     fp.write_bytes(data)
#     return fp
def download_pdf(url: str, tmpdir: Path, session: requests.Session, referer: str | None = None) -> Path:
    # 1) try normal request path (your robust_pdf_get)
    try:
        data = robust_pdf_get(session, url, referer=referer)
        fp = tmpdir / Path(url).name
        fp.write_bytes(data)
        return fp
    except Exception as e:
        print(f"[Warn] requests/http2 download failed ({e}); trying Selenium fallback...")

    # 2) optional guard (env flag)
    if os.getenv("USE_SELENIUM_FALLBACK", "1") != "1":
        raise

    # 3) Selenium → cookies → requests download
    return download_pdf_with_selenium_cookies(url, tmpdir, referer=referer or "https://www.saudiexchange.sa/")

# def fetch_html(url: str) -> str:
#     headers = {
#         "User-Agent": "Mozilla/5.0 (compatible; SISCO-Scraper/1.0)",
#         "Accept-Language": "en-US,en;q=0.9",
#     }
#     r = requests.get(url, headers=headers, timeout=30)
#     r.raise_for_status()
#     return r.text

def extract_detail_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        if DETAIL_PATH_KEY in a["href"]:
            links.append(urljoin(base_url, a["href"]))
    return links

def clean_page(url: str, session) -> Dict[str, Any]:
    html = fetch_html(url, session)
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "form"]):
        tag.decompose()

    # Title & subtitle from .title-base
    title_base = soup.select_one(".title-base")
    if title_base:
        h1 = title_base.find("h1")
        title = h1.get_text(strip=True) if h1 else url.split("/")[-1]
        subtitle_p = title_base.find("p")
        subtitle = subtitle_p.get_text(strip=True) if subtitle_p else None
    else:
        title = soup.title.string.strip() if soup.title else url.split("/")[-1]
        subtitle = None

    # Full-page text (fallback)
    text = soup.get_text(" ", strip=True)

    # Attached PDFs
    attached_docs = []
    for td in soup.find_all("td"):
        if "Attached Documents" in td.get_text():
            link_td = td.find_next("td")
            if link_td:
                for a in link_td.find_all("a", href=True):
                    href = a["href"].strip()
                    if href.lower().endswith(".pdf"):
                        attached_docs.append(href)

    # Template HTML under .container .content
    template_html = None
    content_div = soup.select_one(".container .content")
    if content_div:
        template_html = str(content_div)

    return {
        "url": url,
        "text": text,
        "metadata": {
            "title": title,
            "subtitle": subtitle,
            "source": url,
            "length": len(text),
            "attached_docs": attached_docs,
            "template_html": template_html,
        },
    }

def template_text(html: Optional[str]) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)

# def download_pdf(url: str, tmpdir: Path) -> Path:
#     r = requests.get(url, timeout=60)
#     r.raise_for_status()
#     fp = tmpdir / Path(url).name
#     fp.write_bytes(r.content)
#     return fp

# Idempotency helpers (using MongoInterface.db directly)
def find_press_by_url(mongo: MongoInterface, url: str) -> Optional[dict]:
    return mongo.db.PressRelease.find_one({"Url": url})

def find_doc_by_url(mongo: MongoInterface, pr_id, url: str) -> Optional[dict]:
    return mongo.db.Document.find_one({"Url": url, "PressReleaseId": pr_id})

def has_chunks(mongo: MongoInterface, document_id) -> bool:
    return mongo.db.ProcessedContent.count_documents({"DocumentId": document_id}) > 0


# ----------------- Node A: Scrape all -----------------


def scrape_all_node(state: PressState) -> PressState:
    session = make_session()
    state["_session"] = session  # stash it in state for reuse

    base_url = state.get("base_url", BASE_URL)
    releases = []
    seen = set()
    offset = 0
    while True:
        url = base_url if offset == 0 else f"{base_url}/P{offset}"
        try:
            html = fetch_html(url, session)
        except Exception as e:
            print(f"[Error] Could not fetch {url}: {e}")
            break

        detail_links = extract_detail_links(html, base_url)
        if not detail_links:
            break  # no more pages

        for link in detail_links:
            if link in seen:
                continue
            seen.add(link)
            try:
                pr = clean_page(link, session)
                releases.append(pr)
                print(f"[OK] {pr['metadata']['title']} ({pr['metadata']['length']} chars)")
            except Exception as e:
                print(f"[Error] Failed to scrape {link}: {e}")

        offset += PAGE_STEP
        time.sleep(0.5)  # be polite

    return {"base_url": base_url, "releases": releases, "_session": session}


# ----------------- Node B: Save & Process (idempotent) -----------------
def save_and_process_node(state: PressState) -> PressState:
    mongo = MongoInterface()
    client_id = "SISCO"
    collection_id = "SISCO-Press"
    session: requests.Session = state.get("_session") or make_session()  

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=120)

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)

        for pr in state["releases"]:
            meta = pr["metadata"]
            pr_url = pr["url"]

            # 1) Find or create PressRelease
            existing_pr = find_press_by_url(mongo, pr_url)
            if existing_pr:
                pr_id = existing_pr["_id"]
                print(f"• PR exists: {meta['title']}")
            else:
                pr_id = mongo.create_press_release(
                    url=pr_url,
                    title=meta["title"],
                    subtitle=meta["subtitle"],
                    text=pr["text"],  # text goes to chunks; we keep it here for context
                    collection_id=collection_id,
                    client_id=client_id,
                    template_html=meta.get("template_html"),
                    extracted_fields={},  # to be filled by LLM later
                )
                print(f"• PR created: {meta['title']}  -> {pr_id}")

            # 2) Ensure PR chunks exist (prefer template HTML text)
            if not has_chunks(mongo, pr_id):
                pr_txt = template_text(meta.get("template_html")) or pr["text"]
                if pr_txt and pr_txt.strip():
                    chunks = splitter.split_text(pr_txt)
                    if chunks:
                        mongo.add_processed_chunks(pr_id, chunks)
                        print(f"   → Added PR chunks: {len(chunks)}")
            else:
                print("   → PR chunks already present; skipping.")

            # 3) Each attached PDF: find/create + ensure chunks
            for doc_url in meta.get("attached_docs", []):
                filename = doc_url.split("/")[-1]
                existing_doc = find_doc_by_url(mongo, pr_id, doc_url)

                if existing_doc:
                    doc_id = existing_doc["_id"]
                    print(f"   • PDF exists: {filename}")
                else:
                    doc_id = mongo.create_attached_document(
                        parent_pr_id=pr_id,
                        url=doc_url,
                        filename=filename,
                        client_id=client_id,
                        collection_id=collection_id,
                    )
                    print(f"   • PDF created: {filename} -> {doc_id}")

                if not has_chunks(mongo, doc_id):
                    try:
                        pdf_path = download_pdf(doc_url, tmpdir, session=session,referer="https://www.saudiexchange.sa/" )
                        reader = PDFReader(str(pdf_path))
                        reader.read_all()
                        full_text = "\n\n".join(
                            [p["text"] for p in reader.text_content if p.get("text")]
                        )
                        if full_text.strip():
                            chunks = splitter.split_text(full_text)
                            if chunks:
                                mongo.add_processed_chunks(doc_id, chunks)
                                print(f"      → Added PDF chunks: {len(chunks)}")
                        else:
                            print("      → PDF has no text; skipping chunks.")
                    except Exception as e:
                        print(f"      [Warn] PDF processing failed: {doc_url} ({e})")
                else:
                    print("      → PDF chunks already present; skipping.")

    return state


# ----------------- Graph -----------------
graph = StateGraph(PressState)
graph.add_node("scrape_all", scrape_all_node)
graph.add_node("save_and_process", save_and_process_node)
graph.add_node("extract_entities", extract_entities_node)


graph.set_entry_point("scrape_all")
graph.add_edge("scrape_all", "save_and_process")
graph.add_edge("save_and_process", "extract_entities")
graph.add_edge("extract_entities", END)

app = graph.compile()

if __name__ == "__main__":
    result = app.invoke({"base_url": BASE_URL})
    print(f"✅ Total releases scraped: {len(result['releases'])}")
