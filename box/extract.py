"""Turn free speech into structured scribe records.

Two paths: a fast deterministic parser for the common imperative forms
("received 40 blankets", "distributed 12 cases of water"), and an LLM
fallback for messier utterances. The deterministic path is unit-tested and
runs with no model, so supply logging works even if Gemma is busy.
"""
from __future__ import annotations

import json
import re

from . import llm

_NUM = r"(\d+(?:\.\d+)?)"
_RECV = re.compile(rf"\b(received|got|added|have)\b.*?{_NUM}\s*([a-z ]+)", re.I)
_DIST = re.compile(
    rf"\b(distributed|used|gave|handed out|took)\b.*?{_NUM}\s*([a-z ]+)", re.I)

# common count-units to strip so the item name is clean
_UNITS = ("cases", "case", "gallons", "gallon", "litres", "liters", "litre",
          "liter", "boxes", "box", "bottles", "bottle", "packs", "pack")


def parse_supply(text: str) -> dict | None:
    """-> {item, delta, unit} or None. Deterministic; no model."""
    for rx, sign in ((_DIST, -1), (_RECV, +1)):   # distribute checked first
        m = rx.search(text)
        if not m:
            continue
        qty = float(m.group(2)) * sign
        rest = m.group(3).strip().lower()
        unit = ""
        parts = rest.split()
        if parts and parts[0] in _UNITS:
            unit = parts[0]
            rest = " ".join(parts[1:])
        rest = re.sub(r"\bof\b", "", rest).strip()
        if rest:
            return {"item": rest, "delta": qty, "unit": unit}
    return None


REGISTRY_SYS = (
    "Extract shelter intake fields from the conversation as strict JSON with "
    "keys: names (comma-separated household members), medical (needs or "
    "allergies), missing (unaccounted-for people), phone. Use empty strings "
    "for anything not stated. Output ONLY the JSON object."
)


def extract_registry(transcript: str) -> dict:
    """LLM extraction of registry fields from an interview transcript."""
    raw = llm.generate(transcript, REGISTRY_SYS, num_predict=200)
    return _first_json(raw) or {"names": "", "medical": "", "missing": "",
                                "phone": ""}


def _first_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
