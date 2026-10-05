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
import asyncio
import logging
from typing import Dict, Any, Optional
import httpx
from dotenv import load_dotenv

from app.db import get_database

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()


def compute_communication_score(
    gemini_signals: Dict[str, Any],
    features: Dict[str, Any],
    transcript: str = ""
) -> Dict[str, Any]:
    """
    Python logic to combine Gemini communication signals with measurable audio metrics.
    """
    speaking_rate = features.get("speaking_rate", 0.0) or 0.0
    clean_t = transcript.strip().lower() if transcript else ""
    no_speech_markers = {
        "", "(no transcript recorded)", "[no speech detected]",
        "[silence]", "n/a", "none", "no transcript", "no speech"
    }
    is_no_speech = (
        not clean_t
        or clean_t in no_speech_markers
        or not re.search(r"\b\w+\b", clean_t)
        or (speaking_rate == 0.0 and len(clean_t.split()) <= 2)
    )
    if is_no_speech:
        return {
            "behavior_score": 0.0,
            "explanation": "No audible speech detected.",
            "communication_observation": "No audible speech detected.",
            "filler_count": 0,
            "repeated_disfluency_count": 0,
            "non_substantive_segments": [],
        }

    filler_count = int(gemini_signals.get("filler_count", 0) or 0)
    rep_count = int(gemini_signals.get("repeated_disfluency_count", 0) or 0)
    non_sub_segments = gemini_signals.get("non_substantive_segments", []) or []
    if isinstance(non_sub_segments, str):
        non_sub_segments = [non_sub_segments] if non_sub_segments.strip() else []

    observation = str(gemini_signals.get("communication_observation") or gemini_signals.get("explanation") or "").strip()

    pauses = features.get("pauses", {}) or {}
    pause_count = pauses.get("count", 0) or 0
    long_pauses = pauses.get("long_pauses_count", 0) or 0
    pause_duration = pauses.get("total_duration_seconds", 0.0) or 0.0
    asked_repeat = features.get("asked_repeat", False) or False

    score = 100.0
    deductions = []

    # 1. Fillers deduction (-3 points per filler, max -30)
    if filler_count > 0:
        filler_ded = min(30.0, filler_count * 3.0)
        score -= filler_ded
        deductions.append(f"{filler_count} filler word(s) (-{filler_ded:.0f} pts)")

    # 2. Repeated disfluency / stammering deduction (-4 points per repetition, max -20)
    if rep_count > 0:
        rep_ded = min(20.0, rep_count * 4.0)
        score -= rep_ded
        deductions.append(f"{rep_count} repeated disfluency/stammer(s) (-{rep_ded:.0f} pts)")

    # 3. Pause deduction (-2 per pause, -5 per long pause, max -30)
    pause_ded = min(30.0, (pause_count * 2.0) + (long_pauses * 5.0))
    if pause_ded > 0:
        score -= pause_ded
        deductions.append(f"{pause_count} pause(s) ({long_pauses} long) (-{pause_ded:.0f} pts)")

    # 4. Speaking rate (WPM) deduction
    wpm_ded = 0.0
    if speaking_rate == 0:
        wpm_ded = 25.0
        deductions.append("No audible speech detected (-25 pts)")
    elif speaking_rate < 100:
        wpm_ded = min(25.0, (100.0 - speaking_rate) * 0.5)
        deductions.append(f"Slow pace ({speaking_rate} WPM) (-{wpm_ded:.1f} pts)")
    elif speaking_rate > 180:
        wpm_ded = min(25.0, (speaking_rate - 180.0) * 0.5)
        deductions.append(f"Fast pace ({speaking_rate} WPM) (-{wpm_ded:.1f} pts)")

    score -= wpm_ded

    # 5. Asked repeat deduction (-5 pts)
    if asked_repeat:
        score -= 5.0
        deductions.append("Requested question repetition (-5 pts)")

    # 6. Non-substantive / meaningless / verbal non-response deduction
    words = transcript.strip().split() if transcript else []
    total_words = len(words)

    if non_sub_segments:
        non_sub_words_count = 0
        for seg in non_sub_segments:
            seg_words = seg.strip().split()
            non_sub_words_count += len(seg_words)

        ratio = (non_sub_words_count / total_words) if total_words > 0 else 1.0

        if ratio >= 0.7:
            non_sub_ded = 65.0
            deductions.append("Response consists primarily of non-substantive or off-topic speech (-65 pts)")
        elif ratio >= 0.35:
            non_sub_ded = 40.0
            deductions.append("Significant non-substantive speech segments detected (-40 pts)")
        else:
            non_sub_ded = min(25.0, len(non_sub_segments) * 15.0)
            deductions.append(f"Non-substantive speech segment(s) detected (-{non_sub_ded:.0f} pts)")

        score -= non_sub_ded

    final_score = max(0.0, min(100.0, round(score, 1)))

    if not deductions:
        explanation = observation or f"Excellent communication delivery. Smooth pace ({speaking_rate} WPM) with clear articulation."
    else:
        obs_prefix = f"{observation} " if observation else ""
        explanation = f"{obs_prefix}Delivery score: {final_score}/100. Key factors: {'; '.join(deductions)}."

    return {
        "behavior_score": final_score,
        "explanation": explanation,
        "communication_observation": observation,
        "filler_count": filler_count,
        "repeated_disfluency_count": rep_count,
        "non_substantive_segments": non_sub_segments,
    }


def compute_fallback_behavior_score(
    features: Dict[str, Any],
    transcript: str = "",
    question_text: str = ""
) -> Dict[str, Any]:
    """
    Rubric-based local fallback behavior scoring algorithm.
    Used when Gemini API key is missing, unreachable, rate-limited (429/503), or returns malformed data.
    Uses local speech metrics, pattern rules, and local LSA/domain relevance signals.
    """
    from app.services.features import _count_fillers, _count_repetitions
    from app.services.scoring import compute_lsa_similarity, _extract_domain_keywords

    speaking_rate = features.get("speaking_rate", 0.0) or 0.0
    clean_t = transcript.strip().lower() if transcript else ""
    no_speech_markers = {
        "", "(no transcript recorded)", "[no speech detected]",
        "[silence]", "n/a", "none", "no transcript", "no speech"
    }
    is_no_speech = (
        not clean_t
        or clean_t in no_speech_markers
        or not re.search(r"\b\w+\b", clean_t)
        or (speaking_rate == 0.0 and len(clean_t.split()) <= 2)
    )
    if is_no_speech:
        return {
            "behavior_score": 0.0,
            "explanation": "No audible speech detected.",
            "communication_observation": "No audible speech detected.",
            "filler_count": 0,
            "repeated_disfluency_count": 0,
            "non_substantive_segments": [],
            "is_fallback": True,
        }

    fillers = _count_fillers(transcript) if transcript else (features.get("fillers", 0) or 0)
    repetitions = _count_repetitions(transcript) if transcript else (features.get("repetitions", 0) or 0)

    non_substantive = []
    if transcript:
        lower_t = transcript.lower().strip()
        words = re.findall(r"\b\w+\b", lower_t)
        total_words = len(words)

        # 1. Numeric / Random nonsense (e.g., "6666666666")
        is_numeric_nonsense = bool(re.match(r"^[\d\s\W_]+$", lower_t))

        # 2. Obvious verbal non-response (e.g., "I don't know babe you tell me")
        is_verbal_non_response = bool(
            re.search(r"\b(i don'?t know|babe|you tell me|whatever|no idea|dunno|not sure|idk)\b", lower_t)
        )

        # 3. Repeated nonsense / extreme repetition (e.g., "blue job blue job blue job blue job")
        is_repeated_nonsense = (
            (total_words >= 4 and len(set(words)) / total_words <= 0.4)
            or repetitions >= 3
        )

        if is_numeric_nonsense or is_verbal_non_response or is_repeated_nonsense:
            non_substantive.append(transcript)
        elif question_text:
            # 4. Contextual relevance & engagement check (Cases A, B vs Case C, D)
            lsa_sim = compute_lsa_similarity(transcript, question_text)
            q_kw = _extract_domain_keywords(question_text)
            generic_prompt_words = {
                "explain", "describe", "what", "how", "define", "briefly",
                "tell", "about", "work", "works", "does", "in", "is", "a", "the",
                "sentence", "main", "idea", "implemented", "concept", "method",
                "approach", "question", "answer", "one", "two", "three", "following", "given"
            }
            q_topic_kw = q_kw - generic_prompt_words

            t_kw = _extract_domain_keywords(transcript)

            cs_domain_keywords = {
                "sort", "sorting", "algorithm", "array", "element", "elements", "minimum", "maximum",
                "swap", "swapping", "order", "list", "index", "compare", "portion", "sorted", "unsorted",
                "node", "tree", "hash", "stack", "queue", "pointer", "memory", "recursion", "recursive",
                "database", "binary", "complexity", "moving", "select", "selecting", "search"
            }

            has_q_topic_match = len(t_kw & q_topic_kw) > 0
            has_domain_match = len(t_kw & cs_domain_keywords) > 0

            # LSA similarity alone without topic or domain grounding is insufficient for relevance
            is_relevant = (has_q_topic_match and (has_domain_match or lsa_sim >= 0.15)) or (has_domain_match and lsa_sim >= 0.15)

            if not is_relevant:
                non_substantive.append(transcript)

    gemini_signals = {
        "filler_count": fillers,
        "repeated_disfluency_count": repetitions,
        "non_substantive_segments": non_substantive,
        "communication_observation": "Evaluated using local deterministic speech & relevance fallback pipeline.",
    }

    result = compute_communication_score(gemini_signals, features, transcript)
    result["is_fallback"] = True
    return result


async def _call_gemini_api(prompt: str, model_name: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Helper to execute a single HTTP POST request to Gemini REST API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1,
        },
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Gemini API model {model_name} returned HTTP status {response.status_code}: {response.text}"
                )
                return None
        except Exception as exc:
            logger.warning(f"Error calling Gemini model {model_name}: {exc}")
            return None


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
        clean_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
        clean_text = re.sub(r"\s*```$", "", clean_text)

        parsed = json.loads(clean_text)
        if not isinstance(parsed, dict):
            return None

        filler_count = int(parsed.get("filler_count", 0) or 0)
        rep_count = int(parsed.get("repeated_disfluency_count", 0) or 0)
        non_sub_raw = parsed.get("non_substantive_segments", [])
        if isinstance(non_sub_raw, list):
            non_substantive_segments = [str(s) for s in non_sub_raw if s]
        elif isinstance(non_sub_raw, str) and non_sub_raw.strip():
            non_substantive_segments = [non_sub_raw.strip()]
        else:
            non_substantive_segments = []

        observation = str(parsed.get("communication_observation") or parsed.get("explanation") or "").strip()

        return {
            "filler_count": max(0, filler_count),
            "repeated_disfluency_count": max(0, rep_count),
            "non_substantive_segments": non_substantive_segments,
            "communication_observation": observation,
        }
    except Exception as e:
        logger.warning(f"Failed to parse Gemini response JSON: {e}")
        return None


async def score_behavior(
    features: Dict[str, Any],
    transcript: str = "",
    question_text: str = ""
) -> Dict[str, Any]:
    """
    Score candidate communication behavior using Gemini contextual analysis + Python metrics calculation.
    Enforces a strict maximum of ONE Gemini API request per answer.
    """
    speaking_rate = features.get("speaking_rate", 0.0) or 0.0
    clean_t = transcript.strip().lower() if transcript else ""
    no_speech_markers = {
        "", "(no transcript recorded)", "[no speech detected]",
        "[silence]", "n/a", "none", "no transcript", "no speech"
    }
    is_no_speech = (
        not clean_t
        or clean_t in no_speech_markers
        or not re.search(r"\b\w+\b", clean_t)
        or (speaking_rate == 0.0 and len(clean_t.split()) <= 2)
    )
    if is_no_speech:
        logger.info("No audible speech detected / empty transcript. Returning 0/100 score without calling Gemini.")
        return {
            "behavior_score": 0.0,
            "explanation": "No audible speech detected.",
            "communication_observation": "No audible speech detected.",
            "filler_count": 0,
            "repeated_disfluency_count": 0,
            "non_substantive_segments": [],
            "is_fallback": True,
        }

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.info("GEMINI_API_KEY not set. Using rubric-based fallback scoring.")
        return compute_fallback_behavior_score(features, transcript, question_text)

    speaking_rate = features.get("speaking_rate", 0.0) or 0.0
    pauses = features.get("pauses", {}) or {}
    pause_count = pauses.get("count", 0) or 0
    long_pauses = pauses.get("long_pauses_count", 0) or 0
    pause_duration = pauses.get("total_duration_seconds", 0.0) or 0.0
    asked_repeat = features.get("asked_repeat", False) or False

    prompt = (
        "You are an expert speech and communication analyzer evaluating a candidate's spoken interview delivery.\n\n"
        f"Interview Question: \"{question_text or 'N/A'}\"\n"
        f"Candidate Raw Spoken Transcript: \"{transcript or ''}\"\n\n"
        "Measured Spoken Audio Metrics:\n"
        f"- Speaking Rate: {speaking_rate} WPM\n"
        f"- Pause Count: {pause_count} (Total Pause Duration: {pause_duration}s, Long Pauses >=1.5s: {long_pauses})\n"
        f"- Requested Question Repetition: {asked_repeat}\n\n"
        "Analyze the candidate's raw spoken transcript in relation to the question, alongside measured audio metrics:\n"
        "1. filler_count: Count of classic filler words (e.g. um, uh, ah, hmm, like, you know, basically, etc.) used in context.\n"
        "2. repeated_disfluency_count: Count of stammered/repeated words (e.g. 'I I I') or repeated disfluent phrases (e.g. 'blue job blue job').\n"
        "3. non_substantive_segments: Array of strings/phrases that are meaningless, gibberish, obvious verbal non-responses (e.g. 'I don't know', 'babe you tell me'), or off-topic banter.\n"
        "4. communication_observation: A brief 1-2 sentence summary observation of speech delivery fluency.\n\n"
        "IMPORTANT RULES:\n"
        "- Do NOT judge technical accuracy or correctness. Gemini is NOT evaluating technical correctness.\n"
        "- Do NOT define a filler as a word missing from reference answer. Valid explanations use words outside reference answers.\n"
        "- Do NOT generate long explanations.\n"
        "- Output ONLY a valid JSON object matching the keys: 'filler_count', 'repeated_disfluency_count', 'non_substantive_segments', 'communication_observation'.\n"
    )

    try:
        logger.info(f"Sending single request to Gemini API ({DEFAULT_GEMINI_MODEL})...")
        res_data = await _call_gemini_api(prompt, DEFAULT_GEMINI_MODEL, api_key)
        if res_data:
            parsed = _parse_gemini_response(res_data)
            if parsed:
                logger.info(f"Gemini speech analysis successful via {DEFAULT_GEMINI_MODEL}: {parsed}")
                result = compute_communication_score(parsed, features, transcript)
                result["is_fallback"] = False
                return result
    except Exception as exc:
        logger.warning(f"Error executing Gemini communication API call: {exc}")

    logger.warning("Gemini API call failed or returned non-200. Falling back immediately to deterministic rubric scoring.")
    return compute_fallback_behavior_score(features, transcript, question_text)


async def score_answer_behavior(answer_id: str, transcript: str = None, question_text: str = None) -> Dict[str, Any]:
    """
    Score behavior for a given answer_id and persist result into MongoDB score_results.
    """
    from bson import ObjectId

    db = get_database()

    if transcript is None or question_text is None:
        query = {"_id": ObjectId(answer_id)} if ObjectId.is_valid(answer_id) else {"_id": answer_id}
        answer_doc = await db["answers"].find_one(query)
        if answer_doc:
            if transcript is None:
                transcript = answer_doc.get("transcript", "")
            if question_text is None and answer_doc.get("question_id"):
                q_id = answer_doc.get("question_id")
                q_doc = await db["questions"].find_one({"question_id": q_id})
                if not q_doc and ObjectId.is_valid(str(q_id)):
                    q_doc = await db["questions"].find_one({"_id": ObjectId(str(q_id))})
                if q_doc:
                    question_text = q_doc.get("question", "")

    score_doc = await db["score_results"].find_one({"answer_id": answer_id})

    if not score_doc or "features" not in score_doc:
        from app.routers.interview import get_answer_features
        feat_res = await get_answer_features(answer_id)
        features = feat_res.get("features", {})
    else:
        features = score_doc.get("features", {})

    scoring_result = await score_behavior(features, transcript=transcript or "", question_text=question_text or "")

    behavior_score = scoring_result["behavior_score"]
    explanation = scoring_result["explanation"]

    await db["score_results"].update_one(
        {"answer_id": answer_id},
        {
            "$set": {
                "behavior_score": behavior_score,
                "behavior_explanation": explanation,
                "explanation": explanation,
                "communication_observation": scoring_result.get("communication_observation", explanation),
                "filler_count": scoring_result.get("filler_count", 0),
                "repeated_disfluency_count": scoring_result.get("repeated_disfluency_count", 0),
                "non_substantive_segments": scoring_result.get("non_substantive_segments", []),
            }
        },
        upsert=True,
    )

    return {
        "answer_id": answer_id,
        "behavior_score": behavior_score,
        "explanation": explanation,
        "communication_observation": scoring_result.get("communication_observation", explanation),
        "filler_count": scoring_result.get("filler_count", 0),
        "repeated_disfluency_count": scoring_result.get("repeated_disfluency_count", 0),
        "non_substantive_segments": scoring_result.get("non_substantive_segments", []),
        "is_fallback": scoring_result.get("is_fallback", False),
    }

