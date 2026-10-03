"""
Module 7 — Phase B: Live LSA Content Evaluation Service.

Loads the fitted TF-IDF + TruncatedSVD pipeline trained on the Mohler dataset (Data.csv) and computes:
1. Cosine similarity between candidate transcript and reference answer in SVD latent space.
2. Semantic rubric point coverage against candidate transcript.
3. Combined correctness_score (0-100) and updates MongoDB score_results document.

Raises RuntimeError if the trained LSA model file (lsa_pipeline.joblib) is missing.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional
import numpy as np
import joblib
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from app.db import get_database

logger = logging.getLogger(__name__)

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAVED_MODEL_PATH = os.path.join(backend_dir, "data", "lsa_pipeline.joblib")

_LSA_PIPELINE = None


def load_lsa_pipeline() -> Dict[str, Any]:
    """Load or lazily cache the fitted TF-IDF + TruncatedSVD pipeline."""
    global _LSA_PIPELINE
    if _LSA_PIPELINE is not None:
        return _LSA_PIPELINE

    if os.path.exists(SAVED_MODEL_PATH):
        try:
            _LSA_PIPELINE = joblib.load(SAVED_MODEL_PATH)
            logger.info(f"Loaded real trained LSA pipeline from {SAVED_MODEL_PATH}")
            return _LSA_PIPELINE
        except Exception as e:
            raise RuntimeError(f"Failed to load trained LSA model from {SAVED_MODEL_PATH}: {e}")

    error_msg = (
        f"Real trained LSA model file not found at {SAVED_MODEL_PATH}. "
        "Please train the LSA pipeline first by running: python scripts/train_lsa.py"
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)


def _clean_text(text: str) -> str:
    """Clean HTML tags and whitespace."""
    if not text:
        return ""
    text_clean = re.sub(r"<[^>]+>", " ", text)
    text_clean = re.sub(r"\s+", " ", text_clean).strip()
    return text_clean


def compute_lsa_similarity(text1: str, text2: str) -> float:
    """
    Compute cosine similarity between text1 and text2 in SVD latent space.
    Returns float in range [0.0, 1.0].
    """
    t1_clean = _clean_text(text1)
    t2_clean = _clean_text(text2)

    if not t1_clean or not t2_clean:
        return 0.0

    pipeline = load_lsa_pipeline()
    vectorizer = pipeline["vectorizer"]
    svd = pipeline["svd"]

    try:
        tfidf = vectorizer.transform([t1_clean, t2_clean])
        svd_vecs = svd.transform(tfidf)

        norm1 = np.linalg.norm(svd_vecs[0])
        norm2 = np.linalg.norm(svd_vecs[1])

        if norm1 == 0 or norm2 == 0:
            return 0.0

        dot_product = np.dot(svd_vecs[0], svd_vecs[1])
        cosine_sim = dot_product / (norm1 * norm2)
        return float(np.clip(cosine_sim, 0.0, 1.0))
    except Exception as e:
        logger.error(f"Error computing LSA similarity: {e}")
        return 0.0


def evaluate_rubric(transcript: str, rubric: List[str], threshold: float = 0.50) -> Dict[str, Any]:
    """
    Check semantic presence of each rubric point in transcript.
    Uses strict keyword token overlap and calibrated LSA similarity thresholds
    to eliminate false-positive rubric matches.
    """
    if not rubric:
        return {
            "matched_count": 0,
            "total_count": 0,
            "score": 100.0,
            "details": [],
        }

    clean_transcript = _clean_text(transcript).lower()
    transcript_words = set(re.findall(r"\b\w+\b", clean_transcript))

    matched_count = 0
    details = []

    for point in rubric:
        # Strip leading numbering like "1. ", "2) ", etc.
        clean_point = re.sub(r"^\s*\d+[.)]\s*", "", _clean_text(point)).strip()
        sim = compute_lsa_similarity(transcript, clean_point)

        # Extract meaningful non-stop keywords from the rubric point
        point_words = set(re.findall(r"\b\w+\b", clean_point.lower()))
        keywords = {w for w in point_words if len(w) > 2 and w not in ENGLISH_STOP_WORDS}

        overlap = len(keywords.intersection(transcript_words))
        overlap_ratio = overlap / len(keywords) if keywords else 0.0

        # Calibrated matching criteria to prevent false positives:
        # 1. High LSA similarity (>= 0.55) AND at least 1 keyword match (if keywords exist)
        # 2. OR very high LSA similarity (>= 0.65)
        # 3. OR strong keyword overlap ratio (>= 0.50)
        is_matched = (
            (sim >= 0.55 and (overlap > 0 or not keywords))
            or (sim >= 0.65)
            or (overlap_ratio >= 0.50)
        )

        if is_matched:
            matched_count += 1

        details.append({
            "rubric_point": clean_point,
            "matched": bool(is_matched),
            "similarity": round(float(sim), 4),
            "token_overlap_ratio": round(float(overlap_ratio), 4),
        })

    coverage_score = (matched_count / len(rubric)) * 100.0

    return {
        "matched_count": matched_count,
        "total_count": len(rubric),
        "score": round(coverage_score, 1),
        "details": details,
    }


def score_correctness(transcript: str, reference_answer: str, rubric: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Compute combined correctness score (0-100) from LSA similarity and rubric coverage.
    """
    rubric = rubric or []

    # 1. Raw LSA similarity with reference answer
    lsa_sim = compute_lsa_similarity(transcript, reference_answer)
    lsa_score_100 = round(lsa_sim * 100.0, 1)

    # 2. Rubric coverage evaluation
    rubric_eval = evaluate_rubric(transcript, rubric)
    rubric_score_100 = rubric_eval["score"]

    # 3. Combined score (50% LSA similarity + 50% Rubric coverage)
    if rubric:
        combined_score = round(0.5 * lsa_score_100 + 0.5 * rubric_score_100, 1)
    else:
        combined_score = lsa_score_100

    combined_score = max(0.0, min(100.0, combined_score))

    return {
        "correctness_score": combined_score,
        "lsa_similarity_score": lsa_score_100,
        "rubric_coverage_score": rubric_score_100,
        "matched_rubric_points": rubric_eval["matched_count"],
        "total_rubric_points": rubric_eval["total_count"],
        "rubric_details": rubric_eval["details"],
    }


async def score_answer_correctness(answer_id: str) -> Dict[str, Any]:
    """
    Score correctness for a given answer_id and persist result into MongoDB score_results.
    """
    from bson import ObjectId
    from fastapi import HTTPException

    db = get_database()

    # Find answer document
    query = {"_id": ObjectId(answer_id)} if ObjectId.is_valid(answer_id) else {"_id": answer_id}
    answer_doc = await db["answers"].find_one(query)

    if not answer_doc:
        raise HTTPException(status_code=404, detail=f"Answer with id {answer_id!r} not found")

    transcript = answer_doc.get("transcript", "")
    question_id = answer_doc.get("question_id", "")

    # Find question document
    question_doc = await db["questions"].find_one({"question_id": question_id})
    if not question_doc:
        raise HTTPException(status_code=404, detail=f"Question with question_id {question_id!r} not found")

    reference_answer = question_doc.get("reference_answer", "")
    rubric = question_doc.get("rubric", [])

    if isinstance(rubric, str):
        rubric = [r.strip() for r in rubric.split("\n") if r.strip()]

    # Score correctness using real LSA model
    scoring_result = score_correctness(transcript, reference_answer, rubric)

    correctness_score = scoring_result["correctness_score"]

    # Update MongoDB score_results document
    await db["score_results"].update_one(
        {"answer_id": answer_id},
        {
            "$set": {
                "correctness_score": correctness_score,
                "correctness_breakdown": scoring_result,
            }
        },
        upsert=True,
    )

    return {
        "answer_id": answer_id,
        "question_id": question_id,
        "correctness_score": correctness_score,
        "lsa_similarity_score": scoring_result["lsa_similarity_score"],
        "rubric_coverage_score": scoring_result["rubric_coverage_score"],
        "matched_rubric_points": scoring_result["matched_rubric_points"],
        "total_rubric_points": scoring_result["total_rubric_points"],
        "rubric_details": scoring_result["rubric_details"],
    }
