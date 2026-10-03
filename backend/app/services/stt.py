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


async def transcribe_audio(file_path: str) -> Dict[str, Any]:
    """
    Transcribe the given candidate audio file using real available STT providers.
    Raises STTError if no provider is configured or transcription fails.
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

    # Provider 3: Gemini Multimodal Audio Transcription API
    if GEMINI_API_KEY:
        try:
            logger.info(f"Transcribing audio {file_path} via Gemini Multimodal STT API...")
            result = await _transcribe_gemini(file_path)
            logger.info(f"[STT Provider Used: Gemini Multimodal API] Transcript length: {len(result.get('transcript', ''))} chars")
            return result
        except Exception as e:
            logger.warning(f"Gemini Multimodal STT failed: {e}. Attempting fallback STT providers...")

    # Provider 4: Local SpeechRecognition engine (if .wav file format)
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".wav":
        try:
            logger.info(f"Transcribing audio {file_path} via local SpeechRecognition engine...")
            result = await _transcribe_local_speechrecognition(file_path)
            logger.info(f"[STT Provider Used: Local SpeechRecognition] Transcript length: {len(result.get('transcript', ''))} chars")
            return result
        except Exception as e:
            logger.warning(f"Local SpeechRecognition failed: {e}")

    # If all options failed and no working STT key is configured:
    error_msg = (
        "Speech-to-Text transcription failed: No valid STT API key configured or reachable. "
        "Please provide GEMINI_API_KEY, OPENAI_API_KEY, or DEEPGRAM_API_KEY in backend/.env."
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
                else:
                    last_err = f"Model {model} status {res.status_code}: {res.text[:120]}"
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
