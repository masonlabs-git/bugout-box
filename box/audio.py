"""Microphone capture with voice-activity detection (webrtcvad).

Listens continuously; returns a wav path when an utterance completes.
The EMEET's hardware echo cancellation means capture can stay open while
the box is speaking (barge-in friendly).
"""
from __future__ import annotations

import collections
import subprocess
import tempfile
import wave

import webrtcvad

from . import config

FRAME_MS = 30
FRAME_BYTES = int(config.SAMPLE_RATE * FRAME_MS / 1000) * 2  # 16-bit mono
SILENCE_END_MS = 800        # utterance ends after this much trailing silence
MAX_UTTERANCE_S = 20
PREROLL_FRAMES = 10         # keep a little audio from before speech onset


def _arecord():
    return subprocess.Popen(
        ["arecord", "-q", "-D", config.AUDIO_DEVICE, "-f", "S16_LE",
         "-r", str(config.SAMPLE_RATE), "-c", "1", "-t", "raw"],
        stdout=subprocess.PIPE)


def listen_for_utterance(aggressiveness: int = 2) -> str | None:
    """Block until one spoken utterance is captured; return wav path.
    Returns None if the capture process dies."""
    vad = webrtcvad.Vad(aggressiveness)
    proc = _arecord()
    preroll = collections.deque(maxlen=PREROLL_FRAMES)
    voiced: list[bytes] = []
    silence_frames = 0
    in_speech = False
    max_frames = int(MAX_UTTERANCE_S * 1000 / FRAME_MS)
    try:
        while True:
            frame = proc.stdout.read(FRAME_BYTES)
            if len(frame) < FRAME_BYTES:
                return None
            is_speech = vad.is_speech(frame, config.SAMPLE_RATE)
            if not in_speech:
                preroll.append(frame)
                if is_speech:
                    in_speech = True
                    voiced.extend(preroll)
                    silence_frames = 0
            else:
                voiced.append(frame)
                silence_frames = 0 if is_speech else silence_frames + 1
                done = (silence_frames * FRAME_MS >= SILENCE_END_MS
                        or len(voiced) >= max_frames)
                if done:
                    break
    finally:
        proc.terminate()
        proc.wait()

    wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(config.SAMPLE_RATE)
        w.writeframes(b"".join(voiced))
    return wav_path
