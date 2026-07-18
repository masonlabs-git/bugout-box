"""Offline retrieval: SQLite FTS5 (BM25) over the survival corpus.

No vector models, no servers — measured RAM budget on an 8GB Pi leaves no
room for a resident embedder beside Gemma, and BM25 over terminology-rich
field manuals retrieves on par. One .db file on the vault drive.
"""
from __future__ import annotations

import html
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from . import config

SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
    source,             -- short source name, e.g. 'FM 21-76'
    title,              -- article/section title when known
    text,
    tokenize = 'porter unicode61'
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


@dataclass
class Hit:
    source: str
    title: str
    text: str
    score: float

    @property
    def citation(self) -> str:
        return f"{self.source} — {self.title}" if self.title else self.source


def connect(db_path: Path | str = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path or config.INDEX_DB))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(SCHEMA)
    return conn


# ----------------------------------------------------------------- ingest

def _clean(text: str) -> str:
    text = html.unescape(html.unescape(text))   # double-escaped ZIM extracts
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def chunk_text(text: str,
               size: int = config.CHUNK_CHARS,
               overlap: int = config.CHUNK_OVERLAP):
    """Paragraph-packing chunker: fill to ~size chars, break on paragraph
    boundaries when possible, carry a tail overlap for continuity."""
    text = _clean(text)
    if len(text) <= size:
        if text:
            yield text
        return
    paras = re.split(r"\n\s*\n", text)
    buf = ""
    for p in paras:
        p = p.strip()
        if not p:
            continue
        while len(p) > size:          # pathological paragraph: hard split
            head, p = p[:size], p[max(0, size - overlap):]
            if buf:
                yield buf
                buf = ""
            yield head
        if len(buf) + len(p) + 2 > size and buf:
            yield buf
            buf = buf[-overlap:] + "\n\n" + p if overlap else p
        else:
            buf = f"{buf}\n\n{p}" if buf else p
    if buf.strip():
        yield buf.strip()


def ingest_txt(conn: sqlite3.Connection, path: Path, source: str) -> int:
    n = 0
    text = path.read_text(errors="ignore")
    rows = ((source, "", c) for c in chunk_text(text))
    cur = conn.executemany(
        "INSERT INTO chunks(source, title, text) VALUES (?,?,?)", rows)
    n = cur.rowcount
    conn.commit()
    return n


def ingest_jsonl(conn: sqlite3.Connection, path: Path, source: str,
                 max_chunk: int = 2400) -> int:
    """One JSON object per line: {title, text}. Used for the Wikipedia
    medicine extract — bigger chunks to cap row count."""
    n = 0
    batch = []
    with path.open() as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            title = d.get("title", "")
            for c in chunk_text(d.get("text", ""), size=max_chunk):
                batch.append((source, title, c))
            if len(batch) >= 5000:
                conn.executemany(
                    "INSERT INTO chunks(source, title, text) VALUES (?,?,?)",
                    batch)
                conn.commit()
                n += len(batch)
                batch = []
    if batch:
        conn.executemany(
            "INSERT INTO chunks(source, title, text) VALUES (?,?,?)", batch)
        conn.commit()
        n += len(batch)
    return n


# ----------------------------------------------------------------- search

_WORD = re.compile(r"[A-Za-z0-9']+")

# High-frequency function words: excluded from queries — they bloat FTS
# posting-list intersections into multi-second scans on the vault HDD.
STOPWORDS = frozenset(
    "a an and are as at be but by can could do does for from had has have "
    "how i if in is it its me my of on or our should so that the their "
    "them then there these they this to us was we what when where which "
    "who will with would you your".split())

# Authority tier: hand-curated operational sources outrank the Wikipedia
# bulk layer — a shelter answer should cite FM 21-76 or Sphere before trivia.
BULK_SOURCES = ("Wikipedia Medicine",)

# Protocol pins: when a query names a formal protocol, its source is
# guaranteed a seat in the context regardless of BM25's vote — protocol
# coaching must be deterministic, not probabilistic.
PROTOCOL_PINS = {
    "triage": "START Triage Protocol",
    "ics": "NIMS ICS Forms",
}


def _terms(q: str) -> list[str]:
    words = _WORD.findall(q.lower())
    content = [w for w in words if len(w) > 1 and w not in STOPWORDS]
    return content[:8]


def _match(conn: sqlite3.Connection, fq: str, limit: int,
           bulk: bool | None) -> list[Hit]:
    """bulk=False -> authority sources only; True -> bulk only; None -> all."""
    where = "chunks MATCH ?"
    args: list = [fq]
    if bulk is False:
        where += " AND source NOT IN (%s)" % ",".join(
            "?" * len(BULK_SOURCES))
        args += list(BULK_SOURCES)
    elif bulk is True:
        where += " AND source IN (%s)" % ",".join("?" * len(BULK_SOURCES))
        args += list(BULK_SOURCES)
    rows = conn.execute(
        f"SELECT source, title, text, bm25(chunks) AS score "
        f"FROM chunks WHERE {where} ORDER BY score LIMIT ?",
        args + [limit]).fetchall()
    return [Hit(source=r[0], title=r[1], text=html.unescape(r[2]),
                score=r[3]) for r in rows]


def search(conn: sqlite3.Connection, query: str,
           top_k: int = None) -> list[Hit]:
    """Tiered retrieval: AND-precision before OR-recall, authority sources
    before the Wikipedia bulk layer."""
    terms = _terms(query)
    if not terms:
        return []
    k = top_k or config.RETRIEVAL_TOP_K
    and_q = " ".join(f'"{w}"' for w in terms)      # implicit AND
    or_q = " OR ".join(f'"{w}"' for w in terms)

    hits: list[Hit] = []
    seen: set[tuple] = set()

    def take(new: list[Hit]) -> None:
        for h in new:
            key = (h.source, h.title, h.text[:80])
            if key not in seen and len(hits) < k:
                seen.add(key)
                hits.append(h)

    for term, source in PROTOCOL_PINS.items():     # deterministic protocols
        if term in terms:
            rows = conn.execute(
                "SELECT source, title, text, 0.0 FROM chunks "
                "WHERE source = ? LIMIT 2", (source,)).fetchall()
            take([Hit(source=r[0], title=r[1],
                      text=html.unescape(r[2]), score=r[3]) for r in rows])

    take(_match(conn, and_q, k, bulk=False))       # precise + authoritative
    if len(hits) < k:
        take(_match(conn, or_q, k, bulk=False))    # recall, still authority
    if len(hits) < k:
        take(_match(conn, and_q, k, bulk=True))    # precise bulk
    if len(hits) < k:
        take(_match(conn, or_q, k, bulk=True))     # last resort
    return hits


def context_block(hits: list[Hit], budget_chars: int = 3600) -> str:
    """Render hits into the prompt context, trimmed to a char budget so the
    2560-token window never overflows."""
    parts, used = [], 0
    for i, h in enumerate(hits, 1):
        take = h.text[:max(0, budget_chars - used)]
        if not take:
            break
        parts.append(f"[{i}] ({h.citation})\n{take}")
        used += len(take)
    return "\n\n".join(parts)
