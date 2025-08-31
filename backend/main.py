# main.py
import os
import json
import time
import sqlite3
import logging
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError, APITimeoutError

from pinecone import Pinecone
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)

# ---------------- Env & Clients ----------------
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "incident-response-index"

if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY or PINECONE_API_KEY in .env")

# Timeouts (seconds)
OPENAI_TIMEOUT = 20

# Init OpenAI + Pinecone
client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# ---------------- Logging ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("incident-copilot")

# ---------------- SQLite analytics (very simple) ----------------
DB_PATH = os.path.join(os.path.dirname(__file__), "analytics.db")
_conn = sqlite3.connect(DB_PATH)
_conn.execute(
    """
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP,
        alert_text TEXT,
        success INTEGER,
        latency_ms INTEGER,
        error TEXT,
        top_k INTEGER,
        num_sources INTEGER
    )
    """
)
_conn.commit()
_conn.close()

def log_request(alert_text: str, success: bool, latency_ms: int, error: str, top_k: int, num_sources: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO requests(alert_text, success, latency_ms, error, top_k, num_sources) VALUES (?, ?, ?, ?, ?, ?)",
            (alert_text[:500], 1 if success else 0, latency_ms, (error or "")[:500], top_k, num_sources),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Analytics logging failed: {e}")

def _fetch_rows(limit: int) -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT id, ts, alert_text, success, latency_ms, error, top_k, num_sources FROM requests ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# ---------------- FastAPI ----------------
app = FastAPI(title="AI Incident Response Copilot API")

# Restrict CORS in prod; dev for now:
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Schemas ----------------
class AnalyzeRequest(BaseModel):
    alertText: str
    logFile: Optional[Any] = None

class Source(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None
    score: Optional[float] = None

class StructuredOut(BaseModel):
    incident_type: str
    steps: List[str]
    references: List[str]

class AnalyzeResponse(BaseModel):
    alert: str
    context: str
    response: str                 # markdown for current UI
    sources: List[Source]
    structured: Optional[StructuredOut] = None  # machine-usable JSON too

class MetricsRow(BaseModel):
    id: int
    ts: str
    alert_text: str
    success: bool
    latency_ms: int
    error: str | None = None
    top_k: int | None = None
    num_sources: int | None = None

class MetricsSummary(BaseModel):
    count: int
    success_rate: float
    avg_latency_ms: float
    p95_latency_ms: float

# ---------------- Helpers ----------------
def extract_log_indicators(logFile: Optional[dict]) -> str:
    """Pull IPs/users from logs for extra context."""
    if not logFile or not isinstance(logFile, dict):
        return ""
    events = logFile.get("events", [])
    ips = sorted({e.get("ip") for e in events if isinstance(e, dict) and e.get("ip")})
    users = sorted({e.get("user") for e in events if isinstance(e, dict) and e.get("user")})
    bits = []
    if ips:
        bits.append(f"IPs involved: {', '.join(ips)}")
    if users:
        bits.append(f"Users involved: {', '.join(users)}")
    return " | ".join(bits)

# Retry config
_RETRY_EXC = (RateLimitError, APIError, APIConnectionError, APITimeoutError)

@retry(
    retry=retry_if_exception_type(_RETRY_EXC),
    wait=wait_random_exponential(multiplier=1, max=8),
    stop=stop_after_attempt(5),
)
def embed_text(text: str) -> List[float]:
    emb = client.embeddings.create(
        input=text,
        model="text-embedding-3-small",
    )
    return emb.data[0].embedding

@retry(
    retry=retry_if_exception_type(Exception),  # Pinecone raises generic exceptions
    wait=wait_random_exponential(multiplier=1, max=8),
    stop=stop_after_attempt(5),
)
def pinecone_query(vector: List[float], top_k: int = 3):
    return index.query(vector=vector, top_k=top_k, include_metadata=True)

def retrieve_docs(query: str, top_k: int = 3) -> List[dict]:
    vector = embed_text(query)
    res = pinecone_query(vector, top_k=top_k)
    docs = []
    for m in getattr(res, "matches", []) or []:
        meta = m.metadata or {}
        docs.append({
            "title": meta.get("source"),
            "url": meta.get("url"),
            "snippet": (meta.get("text") or "")[:400] + ("..." if meta.get("text") and len(meta["text"]) > 400 else ""),
            "score": getattr(m, "score", None),
        })
    return docs

@retry(
    retry=retry_if_exception_type(_RETRY_EXC),
    wait=wait_random_exponential(multiplier=1, max=8),
    stop=stop_after_attempt(5),
)
def generate_structured(alert: str, context_bits: str, docs: List[dict]) -> dict:
    """Ask GPT to return strict JSON (incident_type, steps[], references[])."""
    # Build compact sources text
    src_lines = []
    for d in docs:
        title = d.get("title") or "Unknown"
        snippet = (d.get("snippet") or "").replace("\n", " ")[:200]
        src_lines.append(f"- {title}: {snippet}")
    sources_text = "\n".join(src_lines) if src_lines else "None"

    system_msg = (
        "You are a concise cybersecurity incident-response copilot. "
        "ALWAYS return valid JSON. No extra text."
    )
    user_msg = f"""
Alert:
{alert}

Context:
{context_bits or "None"}

Relevant reference documents:
{sources_text}

Return ONLY a JSON object with keys:
- "incident_type": short string describing the likely incident (e.g., "Brute Force (T1110)")
- "steps": an array of 3-7 concise, actionable steps
- "references": an array of short source titles (e.g., "NIST SP 800-61", "MITRE ATT&CK T1110")
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=500,
        temperature=0.2,
    )
    content = resp.choices[0].message.content
    return json.loads(content)

def structured_to_markdown(sj: dict, docs: List[dict]) -> str:
    """Convert the structured JSON into a nice markdown block."""
    if not sj:
        return "No response."

    incident = sj.get("incident_type", "Unknown")
    steps = sj.get("steps", [])
    refs = sj.get("references", [])

    md = []
    md.append(f"**Incident Type:** {incident}\n")
    if steps:
        md.append("**Recommended Steps:**")
        for i, step in enumerate(steps, 1):
            md.append(f"{i}. {step}")
        md.append("")

    if not refs and docs:
        refs = [d.get("title") for d in docs if d.get("title")]

    if refs:
        md.append("**References:**")
        for r in refs:
            md.append(f"- {r}")

    return "\n".join(md)

# ---------------- Routes ----------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Incident Response Copilot API is running"}

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    start = time.perf_counter()
    top_k = 3
    try:
        # 1) Indicators from logs
        context_bits = extract_log_indicators(req.logFile)
        query_text = (req.alertText or "").strip()
        if not query_text:
            raise HTTPException(status_code=400, detail="alertText is required.")

        # 2) Retrieve docs (with error handling)
        try:
            docs = retrieve_docs(f"{query_text} {context_bits}".strip(), top_k=top_k)
        except Exception as e:
            logger.exception("Pinecone retrieval failed")
            raise HTTPException(status_code=500, detail=f"Pinecone error: {str(e)}")

        # 3) Ask GPT for structured JSON (with retries)
        try:
            structured_json = generate_structured(query_text, context_bits, docs)
        except (RateLimitError, APIError, APIConnectionError, APITimeoutError) as e:
            logger.exception("OpenAI call failed")
            raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected LLM error")
            raise HTTPException(status_code=500, detail=f"LLM unexpected error: {str(e)}")

        # 4) Build markdown for current UI
        response_md = structured_to_markdown(structured_json, docs)

        latency_ms = int((time.perf_counter() - start) * 1000)
        log_request(req.alertText, True, latency_ms, "", top_k, len(docs))

        return {
            "alert": req.alertText,
            "context": context_bits or "No structured indicators found",
            "response": response_md,              # markdown
            "sources": docs,                      # [{title,url,snippet,score}]
            "structured": structured_json,        # JSON for future UI use
        }

    except HTTPException as http_err:
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_request(req.alertText or "", False, latency_ms, str(http_err.detail), top_k, 0)
        raise

    except Exception as e:
        logger.exception("Unhandled server error")
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_request(req.alertText or "", False, latency_ms, str(e), top_k, 0)
        raise HTTPException(status_code=500, detail="Internal server error")

# --------- NEW: Metrics endpoints ---------
@app.get("/metrics", response_model=List[MetricsRow])
def metrics(limit: int = Query(50, ge=1, le=500)):
    """Return last N requests (most recent first)."""
    rows = _fetch_rows(limit)
    # coerce bool
    for r in rows:
        r["success"] = bool(r["success"])
    return rows

@app.get("/metrics/summary", response_model=MetricsSummary)
def metrics_summary(limit: int = Query(200, ge=1, le=2000)):
    """Return simple summary stats over last N rows."""
    rows = _fetch_rows(limit)
    count = len(rows)
    if count == 0:
        return MetricsSummary(count=0, success_rate=0.0, avg_latency_ms=0.0, p95_latency_ms=0.0)

    successes = sum(1 for r in rows if r["success"])
    success_rate = successes / count

    latencies = sorted(int(r["latency_ms"] or 0) for r in rows)
    avg_latency = sum(latencies) / count if count else 0.0
    # p95
    idx = max(0, int(round(0.95 * (count - 1))))
    p95_latency = float(latencies[idx]) if latencies else 0.0

    return MetricsSummary(
        count=count,
        success_rate=round(success_rate, 4),
        avg_latency_ms=round(avg_latency, 2),
        p95_latency_ms=p95_latency,
    )
