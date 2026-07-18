"""Speech-to-text client. v1: HTTP to the local whisper node (raw wav body).
The interface stays put when STT moves onto the NPU."""
from __future__ import annotations

import requests

from . import config


def transcribe_wav(wav_path: str) -> str:
    with open(wav_path, "rb") as f:
        r = requests.post(config.STT_URL, data=f.read(),
                          headers={"Content-Type": "audio/wav"}, timeout=120)
    r.raise_for_status()
    return r.json().get("text", "").strip()
