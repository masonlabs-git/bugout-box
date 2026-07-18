"""The storybook shelf: public-domain classics read aloud in passages.

"Read Peter Rabbit" -> the actual book, two passages at a time, "next"
to keep going, "stop" to end. Plain Gutenberg text on the vault; no LLM
anywhere in the path, so the words are exactly the author's.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import config

SHELF = Path(config.VAULT) / "storybooks"

# keyword sets -> (spoken title, filename)
BOOKS = {
    ("peter", "rabbit"): ("The Tale of Peter Rabbit", "peter-rabbit.txt"),
    ("grimm",): ("Grimms' Fairy Tales", "grimms-fairy-tales.txt"),
    ("andersen",): ("Andersen's Fairy Tales", "andersens-fairy-tales.txt"),
    ("aesop", "fable"): ("Aesop's Fables", "aesops-fables.txt"),
    ("oz", "wizard"): ("The Wonderful Wizard of Oz", "wizard-of-oz.txt"),
    ("pooh", "winnie"): ("Winnie-the-Pooh", "winnie-the-pooh.txt"),
}

_START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*",
                    re.I | re.S)
_END = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG", re.I)

_cache: dict[str, list[str]] = {}


def match_title(name: str):
    """(title, filename) for a book named any which way, or None."""
    tl = name.lower()
    for keys, entry in BOOKS.items():
        if any(k in tl for k in keys):
            if (SHELF / entry[1]).exists():
                return entry
    return None


def match(text: str):
    """(title, filename) when the utterance names a book on the shelf."""
    tl = text.lower()
    if "read" not in tl and "book" not in tl:
        return None
    return match_title(tl)


def titles_on_shelf() -> list[str]:
    return [t for _, (t, f) in BOOKS.items() if (SHELF / f).exists()]


def passages(filename: str) -> list[str]:
    """Book body split into ~700-char read-aloud passages at paragraph
    boundaries; Gutenberg boilerplate stripped."""
    if filename in _cache:
        return _cache[filename]
    raw = (SHELF / filename).read_text(errors="replace")
    m = _START.search(raw)
    if m:
        raw = raw[m.end():]
    m = _END.search(raw)
    if m:
        raw = raw[:m.start()]
    paras = [re.sub(r"\s+", " ", p).strip()
             for p in re.split(r"\n\s*\n", raw)]
    # drop headings and the front-matter that survives inside the START/
    # END markers (heard live: "Printed and bound in Great Britain by
    # William Clowes Limited" read aloud as the opening of Peter Rabbit)
    _boiler = re.compile(
        r"(?i)printed|published|publisher|copyright|illustrat|"
        r"all rights|isbn|transcriber|ebook|frederick warne|contents")
    paras = [p for p in paras
             if len(p) > 40 and not p.isupper() and not _boiler.search(p)]
    out, buf = [], ""
    for p in paras:
        if len(buf) + len(p) > 700 and buf:
            out.append(buf.strip())
            buf = ""
        buf += " " + p
    if buf.strip():
        out.append(buf.strip())
    _cache[filename] = out
    return out
