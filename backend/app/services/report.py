"""
Module 10 — Report Generation Service.

Aggregates all answers and score_results documents for a completed session into:
- overall technical score (avg correctness_score)
- overall communication score (avg behavior_score)
- overall combined score
- final theta / estimated ability and standard error
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
    topic_breakdown: List[Dict[str, Any]],
    per_question_breakdown: List[Dict[str, Any]],
    overall_technical: float,
    overall_communication: float,
) -> Dict[str, List[str]]:
    """
    Auto-generate 2-3 strengths and 2-3 weaknesses based on candidate's performance
    across topics, correctness scores, missed rubric points, and communication features.
    """
    strengths: List[str] = []
    weaknesses: List[str] = []

    # 1. Topic-level analysis
    if topic_breakdown:
        sorted_by_tech = sorted(topic_breakdown, key=lambda x: x["avg_correctness_score"], reverse=True)
        best_topic = sorted_by_tech[0]
        worst_topic = sorted_by_tech[-1]

        if best_topic["avg_correctness_score"] >= 70.0:
            strengths.append(
                f"Strong technical grasp of {best_topic['topic']} with an average score of {best_topic['avg_correctness_score']:.1f}%."
            )
        else:
            strengths.append(
                f"Demonstrated fundamental awareness in {best_topic['topic']} ({best_topic['avg_correctness_score']:.1f}% score)."
            )

        if worst_topic["avg_correctness_score"] < 75.0:
            weaknesses.append(
                f"Opportunity to deepen knowledge in {worst_topic['topic']}, averaging {worst_topic['avg_correctness_score']:.1f}% correctness."
            )
        else:
            weaknesses.append(
                f"Minor gaps identified in edge cases for {worst_topic['topic']} ({worst_topic['avg_correctness_score']:.1f}% correctness)."
            )

    # 2. Rubric / Technical accuracy analysis
    all_missed_rubric: List[str] = []
    for q in per_question_breakdown:
        all_missed_rubric.extend(q.get("missed_rubric_points", []))

    if overall_technical >= 80.0:
        strengths.append(
            f"High overall technical accuracy ({overall_technical:.1f}%), consistently addressing key concepts in reference answers."
        )
    elif overall_technical >= 60.0:
        strengths.append(
            f"Solid technical foundation ({overall_technical:.1f}%), answering core requirements for most technical questions."
        )

    if all_missed_rubric:
        sample_missed = all_missed_rubric[0]
        if len(sample_missed) > 80:
            sample_missed = sample_missed[:77] + "..."
        weaknesses.append(
            f"Missed specific key rubric points during explanations (e.g. '{sample_missed}')."
        )
    else:
        weaknesses.append(
            "Could expand responses with more detailed implementation examples and technical depth."
        )

    # 3. Speech and Communication analysis
    total_fillers = 0
    total_words = 0
    speaking_rates = []

    for q in per_question_breakdown:
        feats = q.get("features") or {}
        if isinstance(feats, dict):
            total_fillers += feats.get("fillers", 0) or 0
            sr = feats.get("speaking_rate")
            if sr and sr > 0:
                speaking_rates.append(sr)

    avg_wpm = (sum(speaking_rates) / len(speaking_rates)) if speaking_rates else 0.0

    if overall_communication >= 75.0:
        strengths.append(
            f"Clear and structured verbal presentation style with a strong communication score ({overall_communication:.1f}%)."
        )
    elif total_fillers <= 5:
        strengths.append(
            "Maintained concise and articulate delivery with minimal use of filler words."
        )
    else:
        strengths.append(
            "Paced answers thoughtfully and maintained consistent dialogue engagement."
        )

    if total_fillers > 5:
        weaknesses.append(
            f"Frequent use of filler words detected ({total_fillers} total instances across responses); aim for steady pauses instead."
        )
    elif avg_wpm > 0 and (avg_wpm < 110 or avg_wpm > 170):
        weaknesses.append(
            f"Pacing was slightly non-optimal (avg {avg_wpm:.0f} WPM); target a natural speaking rate of 120-150 words per minute."
        )
    elif overall_communication < 70.0:
        weaknesses.append(
            f"Communication score ({overall_communication:.1f}%) indicates scope for clearer explanation structure and delivery."
        )

    # Ensure 2-3 items for strengths and weaknesses
    if len(strengths) < 2:
        strengths.append("Completed all assigned technical interview questions attentively.")
    if len(weaknesses) < 2:
        weaknesses.append("Practice concise summary sentences at the conclusion of complex answers.")

    return {
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
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

        # Query score_results
        score_doc = await db["score_results"].find_one({"answer_id": answer_id})
        if not score_doc:
            score_doc = {}

        corr_score = score_doc.get("correctness_score")
        beh_score = score_doc.get("behavior_score")
        beh_exp = score_doc.get("behavior_explanation") or score_doc.get("explanation")
        features = score_doc.get("features") or {}
        corr_breakdown = score_doc.get("correctness_breakdown") or {}

        # Query questions
        q_doc = await db["questions"].find_one({"question_id": question_id}) or {}
        topic = q_doc.get("topic", "General Computer Science")
        q_text = q_doc.get("question", f"Question {question_id}")
        difficulty = q_doc.get("difficulty", "Medium")
        irt_diff = q_doc.get("irt_difficulty", 0.0)

        # Extract missed rubric points
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

        q_item = {
            "question_id": question_id,
            "question_text": q_text,
            "topic": topic,
            "difficulty": difficulty,
            "irt_difficulty": float(irt_diff),
            "transcript": transcript,
            "response_time_seconds": round(float(response_time), 2),
            "correctness_score": round(float(corr_score), 1) if corr_score is not None else None,
            "behavior_score": round(float(beh_score), 1) if beh_score is not None else None,
            "behavior_explanation": beh_exp,
            "features": features,
            "missed_rubric_points": missed_rubric_points,
        }
        per_question_breakdown.append(q_item)

        # Accumulate topic data
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

    # Step 5: Compute summary scores
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

    final_theta = round(float(session_doc.get("theta", 0.0)), 4)
    standard_error = round(float(session_doc.get("standard_error", 1.0)), 4)
    status = session_doc.get("status", "complete")

    # Step 6: Build topic breakdown
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

    # Step 7: Shape chart-ready data
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

    # Step 8: Auto-generate strengths and weaknesses
    sw_results = _generate_strengths_and_weaknesses(
        topic_breakdown=topic_breakdown,
        per_question_breakdown=per_question_breakdown,
        overall_technical=overall_technical,
        overall_communication=overall_communication,
    )

    # Step 9: Assemble final report document
    report_dict = {
        "session_id": session_id,
        "status": status,
        "overall_technical_score": overall_technical,
        "overall_communication_score": overall_communication,
        "overall_score": overall_combined,
        "final_theta": final_theta,
        "standard_error": standard_error,
        "total_questions_answered": len(per_question_breakdown),
        "per_question_breakdown": per_question_breakdown,
        "topic_breakdown": topic_breakdown,
        "chart_data": chart_data,
        "strengths": sw_results["strengths"],
        "weaknesses": sw_results["weaknesses"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Step 10: Cache in MongoDB reports collection
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
