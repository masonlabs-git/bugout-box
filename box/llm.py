"""Ollama client for Gemma 4 — streaming, thinking OFF (measured: thinking
mode silently burns the whole token budget and the box says nothing)."""
from __future__ import annotations

import json
from typing import Iterator

import requests

from . import config


def generate_stream(prompt: str, system: str,
                    num_predict: int = None) -> Iterator[str]:
    """Yield response text fragments as they generate."""
    body = {
        "model": config.MODEL,
        "system": system,
        "prompt": prompt,
        "stream": True,
        "think": False,
        "options": {
            "num_ctx": config.NUM_CTX,
            "num_predict": num_predict or config.NUM_PREDICT,
        },
        "keep_alive": -1,
    }
    with requests.post(f"{config.OLLAMA_URL}/api/generate", json=body,
                       stream=True, timeout=300) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            d = json.loads(line)
            if d.get("response"):
                yield d["response"]
            if d.get("done"):
                return


def generate(prompt: str, system: str, num_predict: int = None) -> str:
    return "".join(generate_stream(prompt, system, num_predict))


def warmup() -> bool:
    """Pin the model resident (boot-time; cold load measured at ~2 min)."""
    try:
        generate("ready", "Reply with exactly: ready", num_predict=4)
        return True
    except requests.RequestException:
        return False
