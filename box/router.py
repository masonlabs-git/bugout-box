"""LLM fallback router: when the regex fast-paths miss, ask Gemma what
the user MEANT instead of guessing wrong.

Regexes stay first — they're instant and exact when they hit. This runs
only for utterances that reached the answer stage but matched no fast
path, costing ~2 s to route correctly instead of 0 s to route wrong.
The classification is temperature-0 and returns slots; all execution
(ledger math, map lookups) stays deterministic — the model classifies,
it never computes.
"""
from __future__ import annotations

import json
import re

from . import llm

_SYSTEM = "You classify requests for an offline emergency assistant. JSON only."

_PROMPT = """UTTERANCE: "{q}"

Classify into exactly one JSON object:
- {{"kind":"stock","item":"<supply name>"}} — asking how much of a supply is CURRENTLY on hand / in storage. NOT how much is needed or required for some number of people or days — that is "question".
- {{"kind":"supply","direction":"out|in","qty":<number>,"unit":"<unit or empty>","item":"<supply name>"}} — reporting supplies handed out or received.
- {{"kind":"places","place":"<place type>"}} — asking where/how far the nearest place is.
- {{"kind":"recognize"}} — asking to be recognized / who am I, via camera.
- {{"kind":"read","book":"<book name>"}} — asking to read a specific book aloud.
- {{"kind":"story"}} — asking for a made-up/bedtime story.
- {{"kind":"question"}} — anything else: survival, first aid, how-to.

JSON:"""


def _extract_json(text: str) -> dict | None:
    s, e = text.find("{"), text.rfind("}")
    if s < 0 or e <= s:
        return None
    try:
        d = json.loads(text[s:e + 1])
        return d if isinstance(d, dict) and "kind" in d else None
    except ValueError:
        return None


def classify(question: str) -> dict | None:
    """One tiny temperature-0 call; None on any failure (caller falls
    back to the RAG, which is always a safe answer)."""
    try:
        out = "".join(llm.generate_stream(
            _PROMPT.format(q=question.replace('"', "'")), _SYSTEM,
            num_predict=60, temperature=0.0))
        return _extract_json(out)
    except Exception:
        return None
