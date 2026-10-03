"""
Module 5 — Speech Feature Extraction Service.

Extracts behavior and speech delivery metrics from candidate audio recordings,
transcripts, and word-level STT timestamps.

Features extracted:
- Fillers count (um, uh, like, you know, etc.)
- Pause metrics (count, total pause duration, long pauses count)
- Speaking rate (Words Per Minute - WPM)
- Repetitions count (repeated words and consecutive phrases)
- Asked repeat (boolean flag if candidate requested question repetition)
"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Common filler words and multi-word filler phrases
SINGLE_WORD_FILLERS = {"um", "uh", "like", "basically", "actually", "er", "ah", "hmm"}
MULTI_WORD_FILLERS = ["you know", "i mean", "so basically"]

# Question repeat request phrases
REPEAT_REQUEST_PHRASES = [
    "repeat the question",
    "could you repeat",
    "can you repeat",
    "say that again",
    "pardon",
    "what was the question",
    "pardon me",
    "didn't catch that",
    "one more time",
    "repeat that",
]


def extract_features(audio_path: str, transcript: str, words: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extract speech delivery features from transcript and word timestamps.

    :param audio_path: Path to candidate recorded audio file.
    :param transcript: STT transcript text.
    :param words: List of dicts with word timestamp info [{'word': str, 'start': float, 'end': float}, ...]
    :return: Dictionary matching Features Pydantic model schema.
    """
    words = words or []
    clean_transcript = transcript.strip() if transcript else ""

    fillers_count = _count_fillers(clean_transcript)
    pause_metrics = _analyze_pauses(words)
    speaking_rate_wpm = _calculate_speaking_rate(clean_transcript, words)
    repetitions_count = _count_repetitions(clean_transcript)
    asked_repeat_flag = _check_asked_repeat(clean_transcript)

    features = {
        "fillers": fillers_count,
        "pauses": pause_metrics,
        "speaking_rate": speaking_rate_wpm,
        "repetitions": repetitions_count,
        "asked_repeat": asked_repeat_flag,
    }

    logger.info(f"Extracted speech features: {features}")
    return features


def _count_fillers(transcript: str) -> int:
    """Count single and multi-word filler occurrences in transcript."""
    if not transcript:
        return 0

    lower_text = transcript.lower()
    total_fillers = 0

    # Multi-word fillers
    for phrase in MULTI_WORD_FILLERS:
        total_fillers += len(re.findall(r"\b" + re.escape(phrase) + r"\b", lower_text))

    # Single-word fillers
    words = re.findall(r"\b\w+\b", lower_text)
    for word in words:
        if word in SINGLE_WORD_FILLERS:
            total_fillers += 1

    return total_fillers


def _analyze_pauses(words: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze silent gaps/pauses between consecutive words from STT timestamps.

    Pause threshold: gap >= 0.5s
    Long pause threshold: gap >= 1.5s
    """
    if not words or len(words) < 2:
        return {
            "count": 0,
            "total_duration_seconds": 0.0,
            "long_pauses_count": 0,
        }

    pause_count = 0
    total_pause_duration = 0.0
    long_pauses_count = 0

    for i in range(1, len(words)):
        prev_end = words[i - 1].get("end", 0.0)
        curr_start = words[i].get("start", 0.0)
        gap = curr_start - prev_end

        if gap >= 0.5:
            pause_count += 1
            total_pause_duration += gap
            if gap >= 1.5:
                long_pauses_count += 1

    return {
        "count": pause_count,
        "total_duration_seconds": round(total_pause_duration, 2),
        "long_pauses_count": long_pauses_count,
    }


def _calculate_speaking_rate(transcript: str, words: List[Dict[str, Any]]) -> float:
    """Calculate Speaking Rate in Words Per Minute (WPM)."""
    if not transcript:
        return 0.0

    word_list = transcript.split()
    total_words = len(word_list)
    if total_words == 0:
        return 0.0

    duration_seconds = 0.0
    if words and len(words) >= 2:
        start_time = words[0].get("start", 0.0)
        end_time = words[-1].get("end", 0.0)
        duration_seconds = end_time - start_time

    # Fallback to estimated duration if timestamps are missing or invalid
    if duration_seconds <= 0.5:
        duration_seconds = total_words * 0.4  # Assume ~0.4s per word average

    minutes = duration_seconds / 60.0
    wpm = total_words / minutes if minutes > 0 else 0.0
    return round(wpm, 2)


def _count_repetitions(transcript: str) -> int:
    """Count repeated consecutive words and 2-word phrase repetitions."""
    if not transcript:
        return 0

    lower_text = transcript.lower()
    # Find repeated consecutive single words: e.g., "the the", "i i"
    single_repeats = len(re.findall(r"\b(\w+)\s+\1\b", lower_text))
    # Find repeated consecutive 2-word phrases: e.g., "in the in the"
    phrase_repeats = len(re.findall(r"\b(\w+\s+\w+)\s+\1\b", lower_text))

    return single_repeats + phrase_repeats


def _check_asked_repeat(transcript: str) -> bool:
    """Check if candidate asked to repeat the question."""
    if not transcript:
        return False

    lower_text = transcript.lower()
    for phrase in REPEAT_REQUEST_PHRASES:
        if phrase in lower_text:
            return True
    return False
