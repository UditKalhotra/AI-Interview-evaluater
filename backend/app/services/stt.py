"""
Module 4 — Speech-to-Text (STT) Service.

Transcribes candidate spoken audio files (.webm, .wav, .mp3) using real STT providers:
1. Deepgram API (if DEEPGRAM_API_KEY is configured)
2. OpenAI Whisper API (if OPENAI_API_KEY or STT_API_KEY is configured)
3. Gemini Multimodal API (if GEMINI_API_KEY is configured)
4. Local SpeechRecognition engine (for .wav files if available)

If no STT provider is available or all fail, raises STTError with clear actionable message.
Does NOT return fake or hardcoded static transcripts.
"""
import os
import re
import json
import base64
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
import httpx

load_dotenv()

logger = logging.getLogger(__name__)

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or os.getenv("STT_API_KEY", "")).strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()


class STTError(Exception):
    """Raised when Speech-to-Text transcription fails across all providers."""
    pass


_WHISPER_MODEL = None


def _get_local_whisper_model():
    """Lazily load and cache local Whisper model for offline fallback."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        import shutil
        import whisper
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            ffmpeg_dir = os.path.dirname(ffmpeg_exe)
            target_ffmpeg = os.path.join(ffmpeg_dir, "ffmpeg.exe")
            if not os.path.exists(target_ffmpeg) and os.path.exists(ffmpeg_exe):
                try:
                    shutil.copy(ffmpeg_exe, target_ffmpeg)
                except Exception:
                    pass
            if ffmpeg_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        except Exception as e:
            logger.warning(f"Could not configure imageio_ffmpeg for local whisper: {e}")

        logger.info("Loading local Whisper model (tiny.en)...")
        _WHISPER_MODEL = whisper.load_model("tiny.en")
    return _WHISPER_MODEL


async def _transcribe_local_whisper(file_path: str) -> Dict[str, Any]:
    """Transcribe audio files (.webm, .wav, .mp3, etc.) using local Whisper model."""
    model = _get_local_whisper_model()
    result = model.transcribe(file_path)
    transcript = (result.get("text") or "").strip()

    words = []
    segments = result.get("segments", [])
    for seg in segments:
        seg_words = seg.get("words", [])
        for w in seg_words:
            words.append({
                "word": w.get("word", "").strip(),
                "start": round(float(w.get("start", 0.0)), 2),
                "end": round(float(w.get("end", 0.0)), 2),
            })

    if not words and transcript:
        words = _estimate_word_timestamps(transcript)

    return {"transcript": transcript, "words": words}


async def transcribe_audio(file_path: str) -> Dict[str, Any]:
    """
    Transcribe the given candidate audio file using real available STT providers.
    Provider Order:
    1. Deepgram API (if DEEPGRAM_API_KEY is configured)
    2. OpenAI Whisper API (if OPENAI_API_KEY or STT_API_KEY is configured)
    3. Local Whisper engine (offline fallback for .webm, .wav, .mp3)
    4. Local SpeechRecognition engine (offline fallback for .wav files)

    Raises STTError if all providers fail.
    """
    if not os.path.exists(file_path):
        raise STTError(f"Audio file not found: {file_path}")

    # Provider 1: Deepgram API
    if DEEPGRAM_API_KEY:
        try:
            logger.info(f"Transcribing audio {file_path} via Deepgram STT API...")
            result = await _transcribe_deepgram(file_path)
            logger.info(f"[STT Provider Used: Deepgram API] Transcript length: {len(result.get('transcript', ''))} chars")
            return result
        except Exception as e:
            logger.warning(f"Deepgram STT failed: {e}. Attempting fallback STT providers...")

    # Provider 2: OpenAI Whisper API
    if OPENAI_API_KEY:
        try:
            logger.info(f"Transcribing audio {file_path} via OpenAI Whisper STT API...")
            result = await _transcribe_openai(file_path)
            logger.info(f"[STT Provider Used: OpenAI Whisper API] Transcript length: {len(result.get('transcript', ''))} chars")
            return result
        except Exception as e:
            logger.warning(f"OpenAI Whisper STT failed: {e}. Attempting fallback STT providers...")

    # Provider 3: Local Whisper engine (supports .webm, .wav, .mp3, etc.)
    try:
        logger.info(f"Transcribing audio {file_path} via local Whisper engine...")
        result = await _transcribe_local_whisper(file_path)
        logger.info(f"[STT Provider Used: Local Whisper Engine] Transcript length: {len(result.get('transcript', ''))} chars")
        return result
    except Exception as e:
        logger.warning(f"Local Whisper STT failed: {e}. Attempting local SpeechRecognition fallback...", exc_info=True)

    # Provider 4: Local SpeechRecognition engine (if .wav file format)
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".wav":
        try:
            logger.info(f"Transcribing audio {file_path} via local SpeechRecognition engine...")
            result = await _transcribe_local_speechrecognition(file_path)
            logger.info(f"[STT Provider Used: Local SpeechRecognition] Transcript length: {len(result.get('transcript', ''))} chars")
            return result
        except Exception as e:
            logger.warning(f"Local SpeechRecognition failed: {e}", exc_info=True)

    # If all options failed:
    error_msg = (
        "Speech-to-Text transcription failed across all providers (Deepgram, OpenAI, Local Whisper)."
    )
    logger.error(error_msg)
    raise STTError(error_msg)


async def _transcribe_deepgram(file_path: str) -> Dict[str, Any]:
    """Transcribe using Deepgram REST API."""
    url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&punctuate=true&utterances=true"
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

    ext = os.path.splitext(file_path)[1].lower()
    content_type = "audio/webm" if ext == ".webm" else "audio/wav" if ext == ".wav" else "audio/mp3"

    with open(file_path, "rb") as f:
        audio_data = f.read()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers=headers,
            content=audio_data,
            params={"content-type": content_type},
            timeout=30.0,
        )

    if response.status_code != 200:
        raise STTError(f"Deepgram API returned status {response.status_code}: {response.text}")

    data = response.json()
    channel = data["results"]["channels"][0]["alternatives"][0]
    transcript = channel.get("transcript", "").strip()
    words_raw = channel.get("words", [])
    words = [
        {
            "word": w.get("word", ""),
            "start": w.get("start", 0.0),
            "end": w.get("end", 0.0),
            "confidence": w.get("confidence", 1.0),
        }
        for w in words_raw
    ]
    return {"transcript": transcript, "words": words}


async def _transcribe_openai(file_path: str) -> Dict[str, Any]:
    """Transcribe using OpenAI Whisper API with verbose_json for word timestamps."""
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    ext = os.path.splitext(file_path)[1].lower()
    filename = f"audio{ext if ext else '.webm'}"

    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, "audio/webm")}
            data = {
                "model": "whisper-1",
                "response_format": "verbose_json",
                "timestamp_granularities[]": "word",
            }
            response = await client.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=60.0,
            )

    if response.status_code != 200:
        raise STTError(f"OpenAI Whisper API returned status {response.status_code}: {response.text}")

    resp_json = response.json()
    transcript = resp_json.get("text", "").strip()
    words_raw = resp_json.get("words", [])
    words = [
        {
            "word": w.get("word", ""),
            "start": float(w.get("start", 0.0)),
            "end": float(w.get("end", 0.0)),
        }
        for w in words_raw
    ]
    return {"transcript": transcript, "words": words}


async def _transcribe_gemini(file_path: str) -> Dict[str, Any]:
    """Transcribe candidate audio using Gemini Multimodal REST API."""
    ext = os.path.splitext(file_path)[1].lower()
    mime_type = "audio/webm" if ext == ".webm" else "audio/wav" if ext == ".wav" else "audio/mp3"

    with open(file_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    models_to_try = [
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
    ]
    prompt_text = (
        "Transcribe the following spoken audio response accurately into text. "
        "Return ONLY a valid JSON object with key 'transcript' containing the exact spoken words, nothing else."
    )

    last_err = None
    async with httpx.AsyncClient(timeout=40.0) as client:
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt_text},
                        {"inline_data": {"mime_type": mime_type, "data": audio_b64}}
                    ]
                }],
                "generationConfig": {"responseMimeType": "application/json"}
            }

            try:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    res_json = res.json()
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        clean_text = re.sub(r"^```(?:json)?\s*", "", text_part.strip(), flags=re.IGNORECASE)
                        clean_text = re.sub(r"\s*```$", "", clean_text)
                        parsed = json.loads(clean_text)
                        transcript = parsed.get("transcript", "").strip()
                        if transcript:
                            return {
                                "transcript": transcript,
                                "words": _estimate_word_timestamps(transcript),
                            }
                elif res.status_code == 429 or "429" in res.text:
                    logger.warning(f"Gemini API returned status 429 (quota/rate limit) for model {model}. Stopping model iterations to failover immediately.")
                    raise STTError("Gemini API quota exhausted (HTTP status 429)")
                else:
                    last_err = f"Model {model} status {res.status_code}: {res.text[:120]}"
            except STTError:
                raise
            except Exception as exc:
                last_err = str(exc)

    raise STTError(f"Gemini Multimodal STT failed across models: {last_err}")


async def _transcribe_local_speechrecognition(file_path: str) -> Dict[str, Any]:
    """Transcribe .wav files using local SpeechRecognition package."""
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
        transcript = recognizer.recognize_google(audio_data)
        return {
            "transcript": transcript,
            "words": _estimate_word_timestamps(transcript),
        }


def _estimate_word_timestamps(text: str) -> List[Dict[str, Any]]:
    """Estimate word timestamps when provider does not supply explicit word timestamps."""
    words_list = text.split()
    timestamps = []
    current_time = 0.0
    average_word_duration = 0.4  # seconds per word
    for w in words_list:
        end_time = current_time + average_word_duration
        timestamps.append({
            "word": w,
            "start": round(current_time, 2),
            "end": round(end_time, 2),
        })
        current_time = end_time + 0.1
    return timestamps
