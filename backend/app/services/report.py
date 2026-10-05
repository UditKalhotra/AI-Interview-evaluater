"""
Module 10 — Report Generation Service.

Aggregates all answers and score_results documents for a completed session into:
- overall technical score (avg correctness_score)
- overall communication score (avg behavior_score)
- overall combined score
- per-question breakdown table with question topic, text, difficulty, and missed rubric points
- per-topic breakdown and chart-ready score distributions
- auto-generated 2-3 strengths and 2-3 weaknesses
- caching in MongoDB 'reports' collection
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException

from app.db import get_database

logger = logging.getLogger(__name__)


def _generate_strengths_and_weaknesses(
    per_question_breakdown: List[Dict[str, Any]],
    overall_technical: float,
    overall_communication: float,
) -> Dict[str, Any]:
    """
    Auto-generate deterministic, data-grounded summary metrics, strengths,
    improvement areas, and next practice steps based on candidate's exact scores.
    """
    total_q = len(per_question_breakdown)
    strong_qs = []
    partial_qs = []
    weak_qs = []

    for idx, q in enumerate(per_question_breakdown):
        q_label = f"Q{idx + 1}"
        score = q.get("correctness_score")
        score_val = float(score) if score is not None else 0.0
        if score_val >= 70.0:
            strong_qs.append(q_label)
        elif score_val >= 40.0:
            partial_qs.append(q_label)
        else:
            weak_qs.append(q_label)

    strengths: List[str] = []
    weaknesses: List[str] = []
    next_steps: List[str] = []

    # 1. Deterministic Strengths
    if strong_qs:
        strengths.append(f"{len(strong_qs)} of {total_q} responses demonstrated strong technical performance.")
        if len(strong_qs) <= 4:
            strengths.append(f"Your strongest responses were {', '.join(strong_qs)}.")

    if overall_communication >= 70.0:
        strengths.append(f"Communication delivery was strong at {overall_communication:.1f}%.")

    if not strengths:
        strengths.append(f"Completed all {total_q} assigned technical interview questions.")

    # 2. Deterministic Areas to Improve
    if weak_qs or partial_qs:
        needs_review_count = len(weak_qs) + len(partial_qs)
        weaknesses.append(f"Technical Accuracy: {needs_review_count} of {total_q} responses need review.")
        all_improve = weak_qs + partial_qs
        weaknesses.append(f"Focus on the concepts covered by: {', '.join(all_improve)}.")

    if overall_communication >= 70.0 and overall_technical < 70.0:
        weaknesses.append("Your communication delivery is already strong. Your primary improvement area is technical accuracy.")
    elif overall_communication < 70.0 and overall_technical >= 70.0:
        weaknesses.append("Your technical understanding is strong. Focus on improving speech clarity and delivery.")
    elif overall_communication < 70.0 and overall_technical < 70.0:
        weaknesses.append("Both technical accuracy and communication delivery require improvement.")

    # 3. Recommended Next Steps
    if overall_technical < 70.0:
        next_steps.append("Review the concepts behind your lowest-scoring questions and retry this topic.")
    else:
        next_steps.append("Continue to another topic to broaden your preparation.")

    if overall_communication >= 70.0:
        next_steps.append("Maintain your current speech delivery while focusing on technical depth.")
    else:
        next_steps.append("Practice concise, structured verbal explanations.")

    if weak_qs:
        next_steps.append(f"Prioritize the concepts represented by {', '.join(weak_qs)}.")

    return {
        "strong_count": len(strong_qs),
        "partial_count": len(partial_qs),
        "needs_review_count": len(weak_qs),
        "strong_qs": strong_qs,
        "weak_qs": weak_qs,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "next_steps": next_steps,
    }


async def generate_session_report(session_id: str, force_recompute: bool = False) -> Dict[str, Any]:
    """
    Generate or fetch a cached comprehensive report for the given session_id.
    """
    db = get_database()

    # Step 1: Check session existence
    session_doc = await db["sessions"].find_one({"session_id": session_id})
    if not session_doc:
        session_doc = await db["sessions"].find_one({"_id": session_id})

    if not session_doc:
        raise HTTPException(
            status_code=404, detail=f"Interview session {session_id!r} not found"
        )

    # Step 2: Check cached report unless force_recompute is True
    if not force_recompute:
        cached_doc = await db["reports"].find_one({"session_id": session_id})
        if cached_doc and "report" in cached_doc:
            logger.info(f"Returning cached report for session {session_id}")
            report_data = cached_doc["report"]
            if isinstance(report_data, dict):
                return report_data

    # Step 3: Fetch all candidate answers for session
    cursor = db["answers"].find({"session_id": session_id}).sort("created_at", 1)
    answer_docs = await cursor.to_list(length=100)

    per_question_breakdown: List[Dict[str, Any]] = []
    correctness_scores: List[float] = []
    behavior_scores: List[float] = []
    topic_data: Dict[str, Dict[str, Any]] = {}

    # Step 4: Process answers and join score_results & questions collections
    for ans in answer_docs:
        answer_id = str(ans["_id"])
        question_id = ans.get("question_id", "")
        transcript = ans.get("transcript", "")
        response_time = ans.get("response_time_seconds", 0.0)

        score_doc = await db["score_results"].find_one({"answer_id": answer_id})
        if not score_doc:
            score_doc = {}

        corr_score = score_doc.get("correctness_score")
        beh_score = score_doc.get("behavior_score")
        beh_exp = score_doc.get("behavior_explanation") or score_doc.get("explanation")
        features = score_doc.get("features") or {}
        corr_breakdown = score_doc.get("correctness_breakdown") or {}

        q_doc = await db["questions"].find_one({"question_id": question_id}) or {}
        topic = q_doc.get("topic", "General Computer Science")
        q_text = q_doc.get("question", f"Question {question_id}")
        difficulty = q_doc.get("difficulty", "Medium")

        missed_rubric_points: List[str] = []
        rubric_details = corr_breakdown.get("rubric_details") or []
        for rd in rubric_details:
            if isinstance(rd, dict) and not rd.get("matched", False):
                point_str = rd.get("rubric_point", "")
                if point_str:
                    missed_rubric_points.append(point_str)

        if corr_score is not None:
            correctness_scores.append(float(corr_score))
        if beh_score is not None:
            behavior_scores.append(float(beh_score))

        corr_val = float(corr_score) if corr_score is not None else 0.0
        if corr_val >= 70.0:
            q_status = "Strong"
        elif corr_val >= 40.0:
            q_status = "Partial"
        else:
            q_status = "Needs Review"

        q_item = {
            "question_id": question_id,
            "question_text": q_text,
            "topic": topic,
            "difficulty": difficulty,
            "transcript": transcript,
            "response_time_seconds": round(float(response_time), 2),
            "correctness_score": round(float(corr_score), 1) if corr_score is not None else None,
            "behavior_score": round(float(beh_score), 1) if beh_score is not None else None,
            "behavior_explanation": beh_exp,
            "features": features,
            "missed_rubric_points": missed_rubric_points,
            "status": q_status,
        }
        per_question_breakdown.append(q_item)

        if topic not in topic_data:
            topic_data[topic] = {
                "topic": topic,
                "question_count": 0,
                "correctness_sum": 0.0,
                "correctness_count": 0,
                "behavior_sum": 0.0,
                "behavior_count": 0,
            }

        topic_data[topic]["question_count"] += 1
        if corr_score is not None:
            topic_data[topic]["correctness_sum"] += float(corr_score)
            topic_data[topic]["correctness_count"] += 1
        if beh_score is not None:
            topic_data[topic]["behavior_sum"] += float(beh_score)
            topic_data[topic]["behavior_count"] += 1

    overall_technical = (
        round(sum(correctness_scores) / len(correctness_scores), 1)
        if correctness_scores
        else 0.0
    )
    overall_communication = (
        round(sum(behavior_scores) / len(behavior_scores), 1)
        if behavior_scores
        else 0.0
    )
    overall_combined = round(0.7 * overall_technical + 0.3 * overall_communication, 1)

    session_topic = session_doc.get("topic")
    status = session_doc.get("status", "complete")

    topic_breakdown: List[Dict[str, Any]] = []
    for top_name, td in topic_data.items():
        avg_corr = (
            round(td["correctness_sum"] / td["correctness_count"], 1)
            if td["correctness_count"] > 0
            else 0.0
        )
        avg_beh = (
            round(td["behavior_sum"] / td["behavior_count"], 1)
            if td["behavior_count"] > 0
            else 0.0
        )
        avg_comb = round(0.7 * avg_corr + 0.3 * avg_beh, 1)

        topic_breakdown.append({
            "topic": top_name,
            "question_count": td["question_count"],
            "avg_correctness_score": avg_corr,
            "avg_behavior_score": avg_beh,
            "avg_combined_score": avg_comb,
        })

    chart_data = {
        "topics": [t["topic"] for t in topic_breakdown],
        "technical_scores": [t["avg_correctness_score"] for t in topic_breakdown],
        "communication_scores": [t["avg_behavior_score"] for t in topic_breakdown],
        "combined_scores": [t["avg_combined_score"] for t in topic_breakdown],
        "score_breakdown_by_topic": [
            {
                "topic": t["topic"],
                "technical": t["avg_correctness_score"],
                "communication": t["avg_behavior_score"],
                "overall": t["avg_combined_score"],
            }
            for t in topic_breakdown
        ],
    }

    sw_results = _generate_strengths_and_weaknesses(
        per_question_breakdown=per_question_breakdown,
        overall_technical=overall_technical,
        overall_communication=overall_communication,
    )

    report_dict = {
        "session_id": session_id,
        "topic": session_topic,
        "status": status,
        "overall_technical_score": overall_technical,
        "overall_communication_score": overall_communication,
        "overall_score": overall_combined,
        "total_questions_answered": len(per_question_breakdown),
        "strong_count": sw_results["strong_count"],
        "partial_count": sw_results["partial_count"],
        "needs_review_count": sw_results["needs_review_count"],
        "per_question_breakdown": per_question_breakdown,
        "topic_breakdown": topic_breakdown,
        "chart_data": chart_data,
        "strengths": sw_results["strengths"],
        "weaknesses": sw_results["weaknesses"],
        "next_steps": sw_results["next_steps"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db["reports"].update_one(
        {"session_id": session_id},
        {
            "$set": {
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc),
                "report": report_dict,
            }
        },
        upsert=True,
    )

    logger.info(f"Generated and cached report for session {session_id}")
    return report_dict
