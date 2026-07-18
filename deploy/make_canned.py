#!/usr/bin/env python3
"""Pre-synthesize Ember's fixed lines with kokoro (RTF ~3 on the Pi —
far too slow for live speech, perfect for one-time canned lines).

Run on the box with the piper venv:
    ~/piper-venv/bin/python3 deploy/make_canned.py
Writes wavs + manifest.json to <vault>/canned/; box/tts.py plays the
canned wav whenever speak() gets an exactly-matching line.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from box import tts  # noqa: E402  (ACK_LINES stay in one place)
from box import config  # noqa: E402
from box.stories import BOOKS  # noqa: E402

LINES = [
    "This is Ember. Say, hey Ember, when you need me.",
    "Yes? I'm listening.",
    "Hold still. Let me look.",
    "Closing the book. Sweet dreams.",
    *tts.ACK_LINES,
    *[f"{title}. Here we go." for _, (title, _f) in BOOKS.items()],
]

VOICE = "af_heart"


def main() -> None:
    import soundfile as sf
    from kokoro_onnx import Kokoro
    out = Path(config.VAULT) / "canned"
    out.mkdir(parents=True, exist_ok=True)
    k = Kokoro("/home/caleb/kokoro/kokoro-v1.0.int8.onnx",
               "/home/caleb/kokoro/voices-v1.0.bin")
    manifest = {}
    for i, line in enumerate(LINES):
        name = f"canned-{i:02d}.wav"
        samples, sr = k.create(line, voice=VOICE, speed=1.0)
        sf.write(str(out / name), samples, sr)
        manifest[line] = name
        print(f"  {name}  {line[:60]}")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(LINES)} canned lines -> {out}")


if __name__ == "__main__":
    main()
