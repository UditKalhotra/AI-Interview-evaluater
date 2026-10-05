"""
Module 3, 4, 5, 6, 7, 9 — Interview Router & Flow Orchestration.

Manages topic-based technical interview sessions:
- Question TTS audio streaming
- Audio upload, STT transcription, feature extraction
- Gemini communication scoring & LSA technical correctness evaluation
- Sequential topic-based question serving (no IRT, no 5-question limit)
"""
import os
import re
import time
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, File, Form, UploadFile
from fastapi.responses import FileResponse

from bson import ObjectId
from app.db import get_database
from app.services.tts import synthesize_speech, TTSError
from app.services.stt import transcribe_audio, STTError
from app.services.features import extract_features
from app.services.gemini import score_answer_behavior
from app.services.scoring import score_answer_correctness
from app.services.report import generate_session_report

router = APIRouter(prefix="/interview", tags=["interview"])


async def get_topic_questions_state(db, session_id: str, topic: Optional[str] = None):
    """
    Finds answered question IDs for session_id, queries all active questions for topic,
    and returns (next_question, answered_count, total_questions, is_complete).
    """
    answers_cursor = db["answers"].find({"session_id": session_id}).sort("created_at", 1)
    answers_list = await answers_cursor.to_list(length=1000)
    answered_ids = [ans.get("question_id") for ans in answers_list if ans.get("question_id")]

    query = {"active": True}
    if topic:
        query["topic"] = {"$regex": f"^{topic}$", "$options": "i"}

    cursor = db["questions"].find(query)
    all_topic_questions = await cursor.to_list(length=1000)

    for q in all_topic_questions:
        if "_id" in q:
            q["_id"] = str(q["_id"])

    total_questions = len(all_topic_questions)
    answered_count = len(set(answered_ids))

    unanswered_questions = [q for q in all_topic_questions if q.get("question_id") not in answered_ids]

    if unanswered_questions:
        next_q = unanswered_questions[0]
        is_complete = False
    else:
        next_q = None
        is_complete = True

    return next_q, answered_count, total_questions, is_complete


@router.get("/question-audio/{question_id}")
async def get_question_audio(question_id: str):
    """Return spoken audio (mp3) of the given question's text."""
    db = get_database()
    doc = await db["questions"].find_one({"question_id": question_id})
    if doc is None:
        raise HTTPException(
            status_code=404, detail=f"Question {question_id!r} not found"
        )

    question_text = doc.get("question")
    if not question_text:
        raise HTTPException(
            status_code=422,
            detail=f"Question {question_id!r} has no question text to speak",
        )

    try:
        audio_path = await synthesize_speech(question_text, question_id)
    except TTSError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=f"{question_id}.mp3",
    )


@router.post("/submit-answer")
async def submit_answer(
    session_id: str = Form(...),
    question_id: str = Form(...),
    response_time_seconds: float = Form(...),
    file: UploadFile = File(...),
):
    """
    Voice Capture, STT, and Feature Extraction.
    """
    uploads_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "uploads",
    )
    os.makedirs(uploads_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1] or ".webm"
    timestamp = int(time.time())
    safe_session = "".join([c for c in session_id if c.isalnum() or c in ("-", "_")])
    safe_question = "".join([c for c in question_id if c.isalnum() or c in ("-", "_")])
    filename = f"{safe_session}_{safe_question}_{timestamp}{ext}"
    saved_path = os.path.join(uploads_dir, filename)

    try:
        contents = await file.read()
        with open(saved_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded audio file: {e}")

    try:
        stt_result = await transcribe_audio(saved_path)
    except STTError as e:
        raise HTTPException(status_code=500, detail=f"Speech-to-text processing failed: {e}")

    audio_url = f"/uploads/{filename}"
    transcript = stt_result.get("transcript", "")
    words = stt_result.get("words", [])

    db = get_database()
    answer_doc = {
        "session_id": session_id,
        "question_id": question_id,
        "audio_url": audio_url,
        "transcript": transcript,
        "words": words,
        "response_time_seconds": response_time_seconds,
        "created_at": datetime.now(timezone.utc),
    }

    result = await db["answers"].insert_one(answer_doc)
    answer_id = str(result.inserted_id)

    features = extract_features(saved_path, transcript, words)
    score_result_doc = {
        "answer_id": answer_id,
        "correctness_score": None,
        "behavior_score": None,
        "features": features,
    }
    await db["score_results"].insert_one(score_result_doc)

    return {
        "answer_id": answer_id,
        "session_id": session_id,
        "question_id": question_id,
        "audio_url": audio_url,
        "transcript": transcript,
        "response_time_seconds": response_time_seconds,
    }


@router.get("/answer/{answer_id}/features")
async def get_answer_features(answer_id: str):
    """GET endpoint for extracted speech features."""
    db = get_database()
    score_doc = await db["score_results"].find_one({"answer_id": answer_id})

    if score_doc and "features" in score_doc:
        return {
            "answer_id": answer_id,
            "features": score_doc["features"],
        }

    query = {"_id": ObjectId(answer_id)} if ObjectId.is_valid(answer_id) else {"_id": answer_id}
    answer_doc = await db["answers"].find_one(query)

    if not answer_doc:
        raise HTTPException(status_code=404, detail=f"Answer with id {answer_id!r} not found")

    transcript = answer_doc.get("transcript", "")
    words = answer_doc.get("words", [])
    audio_url = answer_doc.get("audio_url", "")

    audio_path = ""
    if audio_url:
        filename = os.path.basename(audio_url)
        uploads_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "uploads",
        )
        audio_path = os.path.join(uploads_dir, filename)

    features = extract_features(audio_path, transcript, words)
    score_result_doc = {
        "answer_id": answer_id,
        "correctness_score": None,
        "behavior_score": None,
        "features": features,
    }
    await db["score_results"].update_one(
        {"answer_id": answer_id},
        {"$set": score_result_doc},
        upsert=True,
    )

    return {
        "answer_id": answer_id,
        "features": features,
    }


@router.get("/answer/{answer_id}/behavior-score")
async def get_answer_behavior_score(answer_id: str):
    """Gemini Behavior/Communication Scoring."""
    try:
        result = await score_answer_behavior(answer_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to score answer behavior: {e}")


@router.get("/answer/{answer_id}/correctness-score")
async def get_answer_correctness_score(answer_id: str):
    """Live LSA Content Evaluation."""
    try:
        result = await score_answer_correctness(answer_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to score answer correctness: {e}")


@router.post("/session/start")
async def start_session(
    session_id: Optional[str] = Form(None),
    topic: Optional[str] = Form(None),
):
    """
    Start / Initialize a new topic-based interview session.
    """
    import uuid
    db = get_database()
    sid = session_id or f"session_{uuid.uuid4().hex[:8]}"

    selected_topic = topic
    if not selected_topic:
        first_q = await db["questions"].find_one({"active": True})
        if first_q:
            selected_topic = first_q.get("topic")

    next_q, answered_count, total_questions, is_complete = await get_topic_questions_state(
        db, session_id=sid, topic=selected_topic
    )

    first_q_id = next_q.get("question_id") if next_q else None

    session_doc = {
        "session_id": sid,
        "topic": selected_topic,
        "current_question_id": first_q_id,
        "status": "in_progress" if not is_complete else "complete",
        "created_at": datetime.now(timezone.utc),
    }

    await db["sessions"].insert_one(session_doc)

    return {
        "session_id": sid,
        "topic": selected_topic,
        "status": session_doc["status"],
        "current_question_id": first_q_id,
        "initial_question": next_q,
        "answered_count": answered_count,
        "total_questions": total_questions,
        "is_complete": is_complete,
    }


@router.get("/session/{session_id}/next-question")
@router.post("/session/{session_id}/next-question")
async def get_next_question(session_id: str):
    """
    Topic-based Next Question Selection & Session State.
    """
    db = get_database()
    session_doc = await db["sessions"].find_one({"session_id": session_id})
    if not session_doc:
        session_doc = await db["sessions"].find_one({"_id": session_id})

    if not session_doc:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    topic = session_doc.get("topic")
    next_q, answered_count, total_questions, is_complete = await get_topic_questions_state(
        db, session_id=session_id, topic=topic
    )

    status = "complete" if is_complete else "in_progress"
    next_q_id = next_q.get("question_id") if next_q else None

    await db["sessions"].update_one(
        {"_id": session_doc["_id"]},
        {"$set": {"status": status, "current_question_id": next_q_id, "updated_at": datetime.now(timezone.utc)}},
    )

    return {
        "session_id": session_id,
        "topic": topic,
        "status": status,
        "is_complete": is_complete,
        "answered_count": answered_count,
        "total_questions": total_questions,
        "next_question_id": next_q_id,
        "next_question": next_q,
        "message": "Topic assessment completed" if is_complete else None,
    }


@router.post("/session/{session_id}/advance")
async def advance_session(
    session_id: str,
    question_id: Optional[str] = Form(None),
    response_time_seconds: Optional[float] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """
    Orchestrates one question-answer cycle for topic-based assessment.
    """
    db = get_database()

    session_doc = await db["sessions"].find_one({"session_id": session_id})
    if not session_doc:
        session_doc = await db["sessions"].find_one({"_id": session_id})

    if not session_doc:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    topic = session_doc.get("topic")

    if session_doc.get("status") == "complete":
        next_q, answered_count, total_questions, _ = await get_topic_questions_state(
            db, session_id=session_id, topic=topic
        )
        return {
            "session_id": session_id,
            "topic": topic,
            "status": "complete",
            "is_complete": True,
            "answered_count": answered_count,
            "total_questions": total_questions,
            "message": "Interview session already complete",
            "next_question_id": None,
            "next_question": None,
        }

    last_answer_summary = None

    if file and file.filename:
        effective_qid = question_id or session_doc.get("current_question_id")
        effective_resp_time = response_time_seconds if response_time_seconds is not None else 2.0

        uploads_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "uploads",
        )
        os.makedirs(uploads_dir, exist_ok=True)
        ext = os.path.splitext(file.filename or "")[1] or ".webm"
        timestamp = int(time.time())
        safe_session = "".join([c for c in session_id if c.isalnum() or c in ("-", "_")])
        safe_question = "".join([c for c in effective_qid if c.isalnum() or c in ("-", "_")])
        filename = f"{safe_session}_{safe_question}_{timestamp}{ext}"
        saved_path = os.path.join(uploads_dir, filename)

        contents = await file.read()
        with open(saved_path, "wb") as f:
            f.write(contents)

        stt_result = await transcribe_audio(saved_path)
        transcript = stt_result.get("transcript", "")
        words = stt_result.get("words", [])
        audio_url = f"/uploads/{filename}"

        answer_doc = {
            "session_id": session_id,
            "question_id": effective_qid,
            "audio_url": audio_url,
            "transcript": transcript,
            "words": words,
            "response_time_seconds": effective_resp_time,
            "created_at": datetime.now(timezone.utc),
        }
        ans_res = await db["answers"].insert_one(answer_doc)
        answer_id = str(ans_res.inserted_id)

        features = extract_features(saved_path, transcript, words)
        score_result_doc = {
            "answer_id": answer_id,
            "correctness_score": None,
            "behavior_score": None,
            "features": features,
        }
        await db["score_results"].insert_one(score_result_doc)

        behavior_result = await score_answer_behavior(answer_id)
        behavior_score = behavior_result.get("behavior_score")

        correctness_result = await score_answer_correctness(answer_id)
        correctness_score = correctness_result.get("correctness_score")

        last_answer_summary = {
            "answer_id": answer_id,
            "question_id": effective_qid,
            "audio_url": audio_url,
            "transcript": transcript,
            "response_time_seconds": effective_resp_time,
            "features": features,
            "behavior_score": behavior_score,
            "behavior_explanation": behavior_result.get("explanation"),
            "correctness_score": correctness_score,
            "correctness_breakdown": correctness_result,
        }

    next_q, answered_count, total_questions, is_complete = await get_topic_questions_state(
        db, session_id=session_id, topic=topic
    )

    status = "complete" if is_complete else "in_progress"
    next_q_id = next_q.get("question_id") if next_q else None
    audio_stream_url = None

    if not is_complete and next_q_id:
        audio_stream_url = f"/interview/question-audio/{next_q_id}"
        if next_q and next_q.get("question"):
            try:
                await synthesize_speech(next_q["question"], next_q_id)
            except TTSError:
                pass

    await db["sessions"].update_one(
        {"_id": session_doc["_id"]},
        {"$set": {"status": status, "current_question_id": next_q_id, "updated_at": datetime.now(timezone.utc)}},
    )

    return {
        "session_id": session_id,
        "topic": topic,
        "status": status,
        "is_complete": is_complete,
        "answered_count": answered_count,
        "total_questions": total_questions,
        "last_answer": last_answer_summary,
        "next_question_id": next_q_id,
        "next_question": next_q,
        "next_question_audio_url": audio_stream_url,
        "message": "Topic assessment completed" if is_complete else None,
    }


@router.get("/session/{session_id}/report")
async def get_session_report(session_id: str, refresh: bool = False):
    """
    Report Generation Endpoint.
    """
    try:
        report = await generate_session_report(session_id=session_id, force_recompute=refresh)
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate session report: {e}")
