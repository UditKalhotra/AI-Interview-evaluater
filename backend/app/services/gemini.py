"""
Module 6 — Gemini Behavior/Communication Scoring Service.

Analyzes speech delivery features extracted in Module 5 (fillers, pauses, speaking rate,
repetitions, asked_repeat) using Gemini API to generate a 0-100 communication score
and natural language explanation.

Features error handling, 1 retry on malformed Gemini API responses, and a deterministic
rubric-based fallback scoring algorithm when Gemini API key is missing or unavailable.
"""

import os
import re
import json
import logging
from typing import Dict, Any, Optional
import httpx
from dotenv import load_dotenv

from app.db import get_database

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
FALLBACK_GEMINI_MODELS = ["gemini-3.7-flash", "gemini-3.6-flash"]


def compute_fallback_behavior_score(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rubric-based fallback behavior scoring algorithm.

    Evaluates delivery metrics deterministically when Gemini API key is missing,
    unreachable, or returns malformed data.
    """
    fillers = features.get("fillers", 0) or 0
    pauses = features.get("pauses", {}) or {}
    pause_count = pauses.get("count", 0) or 0
    long_pauses = pauses.get("long_pauses_count", 0) or 0
    pause_duration = pauses.get("total_duration_seconds", 0.0) or 0.0
    speaking_rate = features.get("speaking_rate", 0.0) or 0.0
    repetitions = features.get("repetitions", 0) or 0
    asked_repeat = features.get("asked_repeat", False) or False

    score = 100.0
    deductions = []

    # 1. Fillers deduction (-3 points per filler, max -30)
    filler_deduction = min(30.0, fillers * 3.0)
    if filler_deduction > 0:
        score -= filler_deduction
        deductions.append(f"{fillers} filler word(s) (-{filler_deduction:.0f} pts)")

    # 2. Pauses deduction (-2 per pause, -5 per long pause, max -30)
    pause_deduction = min(30.0, (pause_count * 2.0) + (long_pauses * 5.0))
    if pause_deduction > 0:
        score -= pause_deduction
        deductions.append(
            f"{pause_count} pause(s) ({long_pauses} long, {pause_duration}s total) (-{pause_deduction:.0f} pts)"
        )

    # 3. Speaking rate deduction (Ideal: 120-160 WPM)
    wpm_deduction = 0.0
    if speaking_rate == 0:
        wpm_deduction = 25.0
        deductions.append("No audible speech detected (-25 pts)")
    elif speaking_rate < 100:
        wpm_deduction = min(25.0, (100.0 - speaking_rate) * 0.5)
        deductions.append(f"Slow pace ({speaking_rate} WPM) (-{wpm_deduction:.1f} pts)")
    elif speaking_rate > 180:
        wpm_deduction = min(25.0, (speaking_rate - 180.0) * 0.5)
        deductions.append(f"Fast pace ({speaking_rate} WPM) (-{wpm_deduction:.1f} pts)")

    score -= wpm_deduction

    # 4. Repetitions deduction (-4 per repetition, max -20)
    rep_deduction = min(20.0, repetitions * 4.0)
    if rep_deduction > 0:
        score -= rep_deduction
        deductions.append(f"{repetitions} repeated phrase(s) (-{rep_deduction:.0f} pts)")

    # 5. Asked repeat deduction (-5 pts)
    if asked_repeat:
        score -= 5.0
        deductions.append("Requested question repetition (-5 pts)")

    final_score = max(0.0, min(100.0, round(score, 1)))

    if not deductions:
        explanation = (
            f"Excellent communication delivery. Smooth speaking rate ({speaking_rate} WPM), "
            "minimal pause interruptions, and clear articulation with no filler words."
        )
    else:
        explanation = (
            f"Candidate achieved a delivery score of {final_score}/100. "
            f"Key observations: {'; '.join(deductions)}."
        )

    return {
        "behavior_score": final_score,
        "explanation": explanation,
        "is_fallback": True,
    }


async def _call_gemini_api(prompt: str, model_name: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Helper to execute an HTTP POST request to Gemini REST API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload)
        if response.status_code != 200:
            logger.warning(
                f"Gemini API model {model_name} returned HTTP status {response.status_code}: {response.text}"
            )
            return None
        return response.json()


def _parse_gemini_response(response_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract and validate JSON payload from Gemini response object."""
    try:
        candidates = response_json.get("candidates", [])
        if not candidates:
            return None

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return None

        raw_text = parts[0].get("text", "").strip()
        # Clean markdown code blocks if present
        clean_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
        clean_text = re.sub(r"\s*```$", "", clean_text)

        parsed = json.loads(clean_text)
        if not isinstance(parsed, dict):
            return None

        raw_score = parsed.get("behavior_score")
        explanation = parsed.get("explanation")

        if raw_score is None or explanation is None:
            return None

        score = float(raw_score)
        score = max(0.0, min(100.0, round(score, 1)))
        explanation = str(explanation).strip()

        return {
            "behavior_score": score,
            "explanation": explanation,
            "is_fallback": False,
        }
    except Exception as e:
        logger.warning(f"Failed to parse Gemini response JSON: {e}")
        return None


async def score_behavior(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score candidate communication behavior from speech features.

    Calls Gemini API with 1 retry on malformed responses, falling back to
    rubric calculation if Gemini API key is missing or fails.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.info("GEMINI_API_KEY not set. Using rubric-based fallback scoring.")
        return compute_fallback_behavior_score(features)

    fillers = features.get("fillers", 0) or 0
    pauses = features.get("pauses", {}) or {}
    pause_count = pauses.get("count", 0) or 0
    long_pauses = pauses.get("long_pauses_count", 0) or 0
    pause_duration = pauses.get("total_duration_seconds", 0.0) or 0.0
    speaking_rate = features.get("speaking_rate", 0.0) or 0.0
    repetitions = features.get("repetitions", 0) or 0
    asked_repeat = features.get("asked_repeat", False) or False

    prompt = (
        "You are an expert AI technical interviewer scoring a candidate's spoken delivery and communication skills.\n"
        "Analyze the following speech delivery features extracted from the candidate's audio response:\n\n"
        f"- Filler words count (um, uh, like, you know): {fillers}\n"
        f"- Pause count: {pause_count} (Total pause duration: {pause_duration}s, Long pauses >=1.5s: {long_pauses})\n"
        f"- Speaking rate: {speaking_rate} Words Per Minute (WPM)\n"
        f"- Repetition count (repeated phrases/words): {repetitions}\n"
        f"- Requested question repetition: {asked_repeat}\n\n"
        "Evaluate the overall communication clarity, pace, confidence, and fluency on a 0-100 scale.\n"
        "Output ONLY a valid JSON object with exact keys 'behavior_score' (number 0-100) and 'explanation' (string 2-3 sentences).\n"
        "Example JSON output:\n"
        '{"behavior_score": 85, "explanation": "The candidate spoke at an optimal pace with clear articulation. Minor filler words were present but did not detract from overall delivery."}'
    )

    models_to_try = [DEFAULT_GEMINI_MODEL] + FALLBACK_GEMINI_MODELS

    # Attempt 1 & Attempt 2 (retry once)
    for attempt in range(2):
        logger.info(f"Sending request to Gemini API (Attempt {attempt + 1})...")
        for model in models_to_try:
            try:
                res_data = await _call_gemini_api(prompt, model, api_key)
                if res_data:
                    parsed = _parse_gemini_response(res_data)
                    if parsed:
                        logger.info(f"Gemini scoring successful via {model}: {parsed}")
                        return parsed
            except Exception as exc:
                logger.warning(f"Error calling Gemini model {model} on attempt {attempt + 1}: {exc}")

    logger.warning("Gemini API calls failed or returned malformed JSON after retry. Falling back to rubric scoring.")
    return compute_fallback_behavior_score(features)


async def score_answer_behavior(answer_id: str) -> Dict[str, Any]:
    """
    Score behavior for a given answer_id and persist result into MongoDB score_results.
    """
    db = get_database()
    score_doc = await db["score_results"].find_one({"answer_id": answer_id})

    if not score_doc or "features" not in score_doc:
        from app.routers.interview import get_answer_features
        feat_res = await get_answer_features(answer_id)
        features = feat_res.get("features", {})
    else:
        features = score_doc.get("features", {})

    scoring_result = await score_behavior(features)

    behavior_score = scoring_result["behavior_score"]
    explanation = scoring_result["explanation"]

    # Update score_results collection document in MongoDB
    await db["score_results"].update_one(
        {"answer_id": answer_id},
        {
            "$set": {
                "behavior_score": behavior_score,
                "behavior_explanation": explanation,
                "explanation": explanation,
            }
        },
        upsert=True,
    )

    return {
        "answer_id": answer_id,
        "behavior_score": behavior_score,
        "explanation": explanation,
        "is_fallback": scoring_result.get("is_fallback", False),
    }
