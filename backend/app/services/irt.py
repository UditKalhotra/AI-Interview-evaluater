"""
Module 8 — IRT Engine (Ability Estimation + Next Question Selection).

Implements 1PL / 2PL Item Response Theory (IRT) model:
- Calculates item response probability P(theta) and Fisher Test Information I(theta).
- Updates candidate ability estimate (theta) and Standard Error (SE) using Maximum A Posteriori (MAP) Newton-Raphson iteration.
- Selects the next unanswered active question whose `irt_difficulty` (b-parameter) best matches updated theta.
- Evaluates stopping rules (max questions limit, SE threshold, or bank exhaustion).
"""

import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

from app.db import get_database

logger = logging.getLogger(__name__)

# Default IRT Parameters
DEFAULT_DISCRIMINATION = 1.0  # 1PL Rasch model discrimination parameter (a)
PRIOR_VARIANCE = 1.0           # Standard Normal prior theta ~ N(0, 1^2)
THETA_MIN = -4.0
THETA_MAX = 4.0


def calculate_item_probability(theta: float, b: float, a: float = DEFAULT_DISCRIMINATION) -> float:
    """
    Calculate 1PL / 2PL IRT response probability P_i(theta).
    P_i(theta) = 1 / (1 + exp(-a * (theta - b)))
    """
    logit = a * (theta - b)
    # Clip logit to avoid overflow in exp
    logit = max(-30.0, min(30.0, logit))
    return 1.0 / (1.0 + math.exp(-logit))


def calculate_information(
    theta: float, b_list: List[float], a_list: Optional[List[float]] = None
) -> float:
    """
    Calculate total Fisher Test Information I(theta), including prior information (1 / prior_variance).
    I(theta) = sum(a_i^2 * P_i(theta) * (1 - P_i(theta))) + (1 / prior_variance)
    """
    if not a_list:
        a_list = [DEFAULT_DISCRIMINATION] * len(b_list)

    info = 1.0 / PRIOR_VARIANCE  # Information from prior theta ~ N(0, 1)

    for b, a in zip(b_list, a_list):
        p = calculate_item_probability(theta, b, a)
        info += (a ** 2) * p * (1.0 - p)

    return info


def calculate_standard_error(
    theta: float, b_list: List[float], a_list: Optional[List[float]] = None
) -> float:
    """
    Calculate Standard Error SE(theta) = 1 / sqrt(I(theta)).
    """
    info = calculate_information(theta, b_list, a_list)
    return 1.0 / math.sqrt(info) if info > 0 else 1.0


def update_theta(
    responses: List[Dict[str, Any]], current_theta: float = 0.0
) -> Tuple[float, float]:
    """
    Update candidate theta given past responses using Newton-Raphson MAP estimation.
    Each response dict contains:
        - "irt_difficulty": float (item b-parameter)
        - "correctness_score": float (0-100 score, converted to proportion u in [0, 1])
        - optional "discrimination": float (a-parameter, defaults to 1.0)

    Returns: (updated_theta, standard_error)
    """
    if not responses:
        se = calculate_standard_error(current_theta, [])
        return current_theta, se

    b_list = [float(r.get("irt_difficulty", 0.0)) for r in responses]
    a_list = [float(r.get("discrimination", DEFAULT_DISCRIMINATION)) for r in responses]

    # Convert correctness score (0-100) to proportion u in [0.0, 1.0]
    u_list = []
    for r in responses:
        raw_score = r.get("correctness_score")
        if raw_score is None:
            u_list.append(0.5)
        else:
            u_list.append(max(0.0, min(100.0, float(raw_score))) / 100.0)

    theta = current_theta
    max_iter = 25
    tolerance = 1e-5

    for _ in range(max_iter):
        # Compute gradient (score function) of log-posterior:
        # g(theta) = sum(a_i * (u_i - P_i(theta))) - (theta / prior_variance)
        grad = - (theta / PRIOR_VARIANCE)
        info = 1.0 / PRIOR_VARIANCE

        for b, a, u in zip(b_list, a_list, u_list):
            p = calculate_item_probability(theta, b, a)
            grad += a * (u - p)
            info += (a ** 2) * p * (1.0 - p)

        if abs(grad) < tolerance:
            break

        delta = grad / info if info > 0 else 0.0
        # Dampen step size if delta is large
        delta = max(-1.0, min(1.0, delta))
        theta += delta

        # Clamp theta within acceptable range [-4.0, 4.0]
        theta = max(THETA_MIN, min(THETA_MAX, theta))

    se = calculate_standard_error(theta, b_list, a_list)
    return round(theta, 4), round(se, 4)


async def select_next_question(
    db: Any,
    answered_question_ids: List[str],
    current_theta: float,
    recent_topics: Optional[List[str]] = None,
    topic_cooldown: int = 2,
) -> Optional[Dict[str, Any]]:
    """
    Select the active unanswered question whose irt_difficulty is closest to current_theta,
    excluding topics from recent_topics (the last `topic_cooldown` topics).
    """
    query = {"active": True}
    if answered_question_ids:
        query["question_id"] = {"$nin": answered_question_ids}

    cursor = db["questions"].find(query)
    unanswered_questions = await cursor.to_list(length=1000)

    if not unanswered_questions:
        return None

    # Filter out topics in the recent_topics cooldown list
    recent_topics = recent_topics or []
    excluded_topics = set(recent_topics[-topic_cooldown:]) if topic_cooldown > 0 and recent_topics else set()

    filtered_pool = [q for q in unanswered_questions if q.get("topic") not in excluded_topics]
    if not filtered_pool:
        # Fall back to full unanswered pool if topic filter empties the pool
        filtered_pool = unanswered_questions

    # Pick question with minimum |irt_difficulty - current_theta|
    best_q = min(
        filtered_pool,
        key=lambda q: abs(float(q.get("irt_difficulty", 0.0)) - current_theta),
    )

    if "_id" in best_q:
        best_q["_id"] = str(best_q["_id"])

    return best_q


async def process_next_question_for_session(
    session_id: str, max_questions: int = 5, se_threshold: float = 0.35
) -> Dict[str, Any]:
    """
    Full IRT Orchestration for a session:
    1. Fetch session state or initialize if missing.
    2. Retrieve all answered questions and their score_results.
    3. Update theta & standard error via IRT MAP formula.
    4. Update session document in MongoDB.
    5. Evaluate stopping rules (max_questions, se_threshold, or no remaining questions).
    6. Select next best matching question if not complete.
    """
    db = get_database()

    # 1. Fetch or initialize session
    session_doc = await db["sessions"].find_one({"_id": session_id})
    if not session_doc:
        session_doc = await db["sessions"].find_one({"session_id": session_id})

    if not session_doc:
        # Initialize new session doc
        new_session = {
            "session_id": session_id,
            "current_question_id": None,
            "theta": 0.0,
            "status": "in_progress",
            "created_at": datetime.now(timezone.utc),
        }
        await db["sessions"].insert_one(new_session)
        session_doc = new_session

    current_theta = float(session_doc.get("theta", 0.0))

    # 2. Fetch answered questions for this session ordered by created_at
    answers_cursor = db["answers"].find({"session_id": session_id}).sort("created_at", 1)
    answers_list = await answers_cursor.to_list(length=1000)

    answered_question_ids = []
    responses = []
    recent_topics = []

    for ans in answers_list:
        q_id = ans.get("question_id")
        ans_id = str(ans.get("_id"))
        if q_id:
            answered_question_ids.append(q_id)

        # Get correctness score from score_results (matching both string and ObjectId formats)
        score_doc = await db["score_results"].find_one({
            "$or": [
                {"answer_id": ans_id},
                {"answer_id": ans.get("_id")},
            ]
        })
        correctness_score = score_doc.get("correctness_score") if score_doc else None

        # Get question's irt_difficulty and topic
        question_doc = await db["questions"].find_one({"question_id": q_id})
        if question_doc:
            irt_diff = float(question_doc.get("irt_difficulty", 0.0))
            topic = question_doc.get("topic")
            if topic:
                recent_topics.append(topic)
        else:
            irt_diff = 0.0

        responses.append({
            "question_id": q_id,
            "irt_difficulty": irt_diff,
            "correctness_score": correctness_score,
        })

    # 3. Update theta and Standard Error based on responses
    updated_theta, se = update_theta(responses, current_theta=current_theta)

    # 4. Check stopping conditions
    answered_count = len(answered_question_ids)
    is_max_reached = answered_count >= max_questions
    is_se_converged = (answered_count >= 2) and (se <= se_threshold)

    unanswered_q = await select_next_question(
        db,
        answered_question_ids=answered_question_ids,
        current_theta=updated_theta,
        recent_topics=recent_topics,
        topic_cooldown=2,
    )

    no_more_questions = unanswered_q is None

    is_complete = is_max_reached or is_se_converged or no_more_questions

    status = "complete" if is_complete else "in_progress"
    next_question_id = None if is_complete else (unanswered_q.get("question_id") if unanswered_q else None)

    # 5. Persist updated session state into MongoDB
    update_data = {
        "theta": updated_theta,
        "standard_error": se,
        "status": status,
        "current_question_id": next_question_id,
        "updated_at": datetime.now(timezone.utc),
    }

    if "_id" in session_doc:
        await db["sessions"].update_one(
            {"_id": session_doc["_id"]},
            {"$set": update_data},
        )
    else:
        await db["sessions"].update_one(
            {"session_id": session_id},
            {"$set": update_data},
            upsert=True,
        )

    response_payload = {
        "session_id": session_id,
        "theta": updated_theta,
        "standard_error": se,
        "status": status,
        "is_complete": is_complete,
        "answered_count": answered_count,
        "next_question_id": next_question_id,
        "next_question": unanswered_q if not is_complete else None,
    }

    if is_complete:
        response_payload["message"] = (
            "Interview completed: max questions reached" if is_max_reached
            else "Interview completed: standard error threshold met" if is_se_converged
            else "Interview completed: no more questions in bank"
        )

    return response_payload
