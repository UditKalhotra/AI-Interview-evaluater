"""
Module 3 — Avatar Voice Output (Text-to-Speech).

Given a question_id, fetches that question's `question` text from Module 2's
`questions` collection, synthesizes it to speech via services/tts.py, and
streams the audio back as audio/mpeg for the frontend avatar to play.

This is the first route under the /interview prefix — later modules
(4, 8, 9...) add more routes here, they don't create a parallel router.
"""
import os
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
from app.services.irt import process_next_question_for_session, select_next_question
from app.services.report import generate_session_report

router = APIRouter(prefix="/interview", tags=["interview"])


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
    Module 4 & Module 5 — Voice Capture, STT, and Feature Extraction.

    Accepts recorded candidate audio for a question, saves it locally,
    transcribes it via STT, inserts an answer document into MongoDB answers collection,
    and extracts speech features into MongoDB score_results collection.
    """
    uploads_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "uploads",
    )
    os.makedirs(uploads_dir, exist_ok=True)

    # Determine extension
    ext = os.path.splitext(file.filename or "")[1]
    if not ext:
        ext = ".webm"

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

    # Transcribe audio using STT service
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

    # Module 5 — Extract speech features and create score_results document
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
    """
    Module 5 — GET endpoint for extracted speech features.

    Returns the features embedded document stored on score_results collection for given answer_id.
    """
    db = get_database()
    score_doc = await db["score_results"].find_one({"answer_id": answer_id})

    if score_doc and "features" in score_doc:
        return {
            "answer_id": answer_id,
            "features": score_doc["features"],
        }

    # Fallback search in answers collection if score_results document missing
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
    """
    Module 6 — Gemini Behavior/Communication Scoring.

    Triggers behavior evaluation for given answer_id using Gemini API (or fallback),
    updates score_results document in MongoDB, and returns the result.
    """
    try:
        result = await score_answer_behavior(answer_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to score answer behavior: {e}")


@router.get("/answer/{answer_id}/correctness-score")
async def get_answer_correctness_score(answer_id: str):
    """
    Module 7 — Live LSA Content Evaluation.

    Calculates correctness score (0-100) using LSA cosine similarity with reference answer
    and rubric coverage analysis, updates score_results in MongoDB, and returns the breakdown.
    """
    try:
        result = await score_answer_correctness(answer_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to score answer correctness: {e}")


@router.post("/session/start")
async def start_session(session_id: str = Form(None)):
    """
    Module 8 — Start / Initialize a new interview session.
    """
    import uuid
    db = get_database()
    sid = session_id or f"session_{uuid.uuid4().hex[:8]}"

    # Select initial question closest to theta = 0.0
    first_q = await select_next_question(db, answered_question_ids=[], current_theta=0.0)
    first_q_id = first_q.get("question_id") if first_q else None

    session_doc = {
        "session_id": sid,
        "current_question_id": first_q_id,
        "theta": 0.0,
        "standard_error": 1.0,
        "status": "in_progress",
        "created_at": datetime.now(timezone.utc),
    }

    await db["sessions"].insert_one(session_doc)
    return {
        "session_id": sid,
        "theta": 0.0,
        "standard_error": 1.0,
        "status": "in_progress",
        "current_question_id": first_q_id,
        "initial_question": first_q,
    }


@router.get("/session/{session_id}/next-question")
@router.post("/session/{session_id}/next-question")
async def get_next_question(
    session_id: str,
    max_questions: int = 5,
    se_threshold: float = 0.35,
):
    """
    Module 8 — IRT Engine Next Question Selection & Ability Estimation.

    Calculates updated ability theta, checks stopping rules, updates session in MongoDB,
    and returns the next matching question_id.
    """
    try:
        result = await process_next_question_for_session(
            session_id=session_id,
            max_questions=max_questions,
            se_threshold=se_threshold,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process IRT next question: {e}")


@router.post("/session/{session_id}/advance")
async def advance_session(
    session_id: str,
    question_id: Optional[str] = Form(None),
    response_time_seconds: Optional[float] = Form(None),
    file: Optional[UploadFile] = File(None),
    max_questions: int = Form(5),
    se_threshold: float = Form(0.35),
):
    """
    Module 9 — Interview Flow Orchestration.

    Orchestrates Modules 3 through 8 in sequence for one question-answer cycle:
    1. If candidate uploaded an answer audio file:
       a. Save audio locally to uploads/ folder.
       b. Transcribe audio via STT (Module 4) & save document to MongoDB answers collection.
       c. Extract speech features (Module 5) into score_results collection.
       d. Trigger Gemini behavior scoring (Module 6).
       e. Trigger LSA correctness scoring (Module 7).
    2. Trigger IRT ability update, standard error calculation, stopping rule check, and next question selection (Module 8).
    3. If interview continues, pre-synthesize TTS question audio (Module 3).
    4. Return full turn response payload to the frontend.
    """
    db = get_database()

    # Step 1: Check existing session or initialize if needed
    session_doc = await db["sessions"].find_one({"session_id": session_id})
    if not session_doc:
        session_doc = await db["sessions"].find_one({"_id": session_id})

    if not session_doc:
        first_q = await select_next_question(db, answered_question_ids=[], current_theta=0.0)
        first_q_id = first_q.get("question_id") if first_q else None
        session_doc = {
            "session_id": session_id,
            "current_question_id": first_q_id,
            "theta": 0.0,
            "standard_error": 1.0,
            "status": "in_progress",
            "created_at": datetime.now(timezone.utc),
        }
        await db["sessions"].insert_one(session_doc)

    if session_doc.get("status") == "complete":
        return {
            "session_id": session_id,
            "status": "complete",
            "is_complete": True,
            "theta": session_doc.get("theta", 0.0),
            "standard_error": session_doc.get("standard_error", 0.0),
            "message": "Interview session already complete",
            "next_question_id": None,
            "next_question": None,
        }

    last_answer_summary = None

    # Step 2: Process uploaded answer audio if provided
    if file and file.filename:
        effective_qid = question_id or session_doc.get("current_question_id")
        if not effective_qid:
            first_q = await select_next_question(db, answered_question_ids=[], current_theta=0.0)
            effective_qid = first_q.get("question_id") if first_q else "MOHLER_1_1"

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

        # STT Transcription (Module 4)
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

        # Speech Feature Extraction (Module 5)
        features = extract_features(saved_path, transcript, words)
        score_result_doc = {
            "answer_id": answer_id,
            "correctness_score": None,
            "behavior_score": None,
            "features": features,
        }
        await db["score_results"].insert_one(score_result_doc)

        # Gemini Behavior Scoring (Module 6)
        behavior_result = await score_answer_behavior(answer_id)
        behavior_score = behavior_result.get("behavior_score")

        # LSA Correctness Scoring (Module 7)
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

    # Step 3: IRT Ability Update & Next Question Selection (Module 8)
    irt_result = await process_next_question_for_session(
        session_id=session_id,
        max_questions=max_questions,
        se_threshold=se_threshold,
    )

    is_complete = irt_result.get("is_complete", False)
    next_q_id = irt_result.get("next_question_id")
    next_q_doc = irt_result.get("next_question")
    audio_stream_url = None

    # Step 4: TTS Question Audio Synthesis for Next Question (Module 3)
    if not is_complete and next_q_id:
        audio_stream_url = f"/interview/question-audio/{next_q_id}"
        if next_q_doc and next_q_doc.get("question"):
            try:
                await synthesize_speech(next_q_doc["question"], next_q_id)
            except TTSError:
                pass

    return {
        "session_id": session_id,
        "status": irt_result.get("status", "in_progress"),
        "is_complete": is_complete,
        "theta": irt_result.get("theta", 0.0),
        "standard_error": irt_result.get("standard_error", 1.0),
        "answered_count": irt_result.get("answered_count", 0),
        "last_answer": last_answer_summary,
        "next_question_id": next_q_id,
        "next_question": next_q_doc,
        "next_question_audio_url": audio_stream_url,
        "message": irt_result.get("message"),
    }


@router.get("/session/{session_id}/report")
async def get_session_report(session_id: str, refresh: bool = False):
    """
    Module 10 — Report Generation Endpoint.

    Aggregates all answers and score_results documents for a completed session into:
    - overall technical score (avg correctness_score)
    - overall communication score (avg behavior_score)
    - final theta / estimated ability
    - per-question breakdown table
    - topic breakdown & chart-ready data
    - auto-generated strengths and weaknesses
    Caches result in 'reports' collection in MongoDB.
    """
    try:
        report = await generate_session_report(session_id=session_id, force_recompute=refresh)
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate session report: {e}")







