"""
Module 3 — Text-to-Speech service.

Provider selection (decided for you, since the shared contract just said
"a TTS API" without naming one):

- If TTS_API_KEY is set in .env -> uses OpenAI's TTS API
  (POST https://api.openai.com/v1/audio/speech, model "tts-1", mp3 output).
  This is the real, production-quality path. OpenAI was picked over
  alternatives (ElevenLabs, Azure, Google Cloud TTS) because it's a single
  REST call with no SDK/service-account setup, is inexpensive, and needs
  exactly one credential.

- If TTS_API_KEY is NOT set -> falls back to gTTS (Google Translate's free
  TTS engine, no API key required at all). This exists purely so Module 3
  is testable end-to-end on a fresh machine with zero credentials. It's a
  dev fallback, not meant for production voice quality.

Either way, generated audio is cached to disk at
backend/uploads/audio/{question_id}.mp3 so repeat requests for the same
question never re-hit the network.
"""
import io
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

TTS_API_KEY = os.getenv("TTS_API_KEY", "").strip()
TTS_MODEL = os.getenv("TTS_MODEL", "tts-1")
TTS_VOICE = os.getenv("TTS_VOICE", "alloy")

# backend/app/services/tts.py -> parents[2] == backend/
AUDIO_CACHE_DIR = Path(__file__).resolve().parents[2] / "uploads" / "audio"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"


class TTSError(Exception):
    """Raised when speech synthesis fails, for either provider."""


def _cache_path(question_id: str) -> Path:
    safe_id = "".join(c for c in question_id if c.isalnum() or c in "-_") or "question"
    return AUDIO_CACHE_DIR / f"{safe_id}.mp3"


async def synthesize_speech(text: str, question_id: str) -> Path:
    """
    Return a local .mp3 file path containing spoken audio of `text`.
    Cached per question_id, so re-requesting the same question is free and
    instant after the first call.
    """
    path = _cache_path(question_id)
    if path.exists() and path.stat().st_size > 0:
        return path

    if TTS_API_KEY:
        audio_bytes = await _synthesize_openai(text)
    else:
        audio_bytes = _synthesize_gtts(text)

    path.write_bytes(audio_bytes)
    return path


async def _synthesize_openai(text: str) -> bytes:
    headers = {
        "Authorization": f"Bearer {TTS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": TTS_MODEL,
        "voice": TTS_VOICE,
        "input": text,
        "response_format": "mp3",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(OPENAI_TTS_URL, headers=headers, json=payload)
    except httpx.HTTPError as e:
        raise TTSError(f"Could not reach OpenAI TTS API: {e}") from e

    if resp.status_code != 200:
        raise TTSError(
            f"OpenAI TTS request failed ({resp.status_code}): {resp.text[:300]}"
        )
    return resp.content


def _synthesize_gtts(text: str) -> bytes:
    try:
        from gtts import gTTS
    except ImportError as e:
        raise TTSError(
            "No TTS_API_KEY is set and gTTS is not installed, so there's no "
            "TTS provider available. Either `pip install gTTS` (free, no key) "
            "or set TTS_API_KEY in backend/.env to use OpenAI's TTS API."
        ) from e

    try:
        buf = io.BytesIO()
        gTTS(text=text, lang="en").write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        raise TTSError(f"gTTS synthesis failed: {e}") from e
