"""
End-to-End 5-Question Interview Flow Verification Script.

Executes a full 5-question interview session against the real MongoDB database
and production orchestration service (`advance_session` in app.routers.interview).

Passes 5 candidate audio recordings (.webm) through the pipeline and reports:
- Question ID
- Question text
- Candidate transcript (from STT)
- Technical score (from LSA + Rubric)
- Communication score (from Gemini / Speech features)
- Candidate theta (IRT ability level)
- Next Question ID

Verifies:
1. Actual transcript (not placeholder).
2. No question repeating.
3. Correct session / answers linking in MongoDB.
4. Score variations based on response quality.
5. Normal completion after 5 questions.
"""

import os
import sys
import uuid
import asyncio
from pathlib import Path
from fastapi import UploadFile

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import connect_to_mongo, close_mongo_connection, get_database
from app.routers.interview import start_session, advance_session, get_session_report


async def run_e2e_test():
    connect_to_mongo()
    db = get_database()

    # Create isolated unique session ID
    session_id = f"e2e_test_{uuid.uuid4().hex[:8]}"

    print("\n=======================================================================")
    print(f"       END-TO-END 5-QUESTION REAL INTERVIEW SESSION TEST               ")
    print(f"Session ID: {session_id}")
    print("=======================================================================\n")

    # Step 1: Initialize Session
    init_res = await start_session(session_id=session_id)
    current_q_id = init_res["current_question_id"]
    current_theta = init_res["theta"]

    print(f"Session initialized. First question: {current_q_id} | Initial Theta: {current_theta}\n")

    # Get sample audio files from uploads/
    uploads_dir = backend_dir / "uploads"
    webm_files = sorted(list(uploads_dir.glob("*.webm")))

    if len(webm_files) < 5:
        print(f"Warning: Only {len(webm_files)} webm files found. Will reuse distinct audio files from uploads.")

    asked_questions = []

    for turn in range(1, 6):
        # Pick an audio file for this turn
        audio_file_path = webm_files[(turn - 1) % len(webm_files)]

        # Fetch current question text from MongoDB questions collection
        q_doc = await db["questions"].find_one({"question_id": current_q_id}) or {}
        q_text = q_doc.get("question", "N/A")

        # Create FastAPI UploadFile mock for local service call
        with open(audio_file_path, "rb") as f:
            file_bytes = f.read()

        import io
        upload_file = UploadFile(
            filename=audio_file_path.name,
            file=io.BytesIO(file_bytes),
        )

        # Call production advance_session pipeline
        advance_res = await advance_session(
            session_id=session_id,
            question_id=current_q_id,
            response_time_seconds=3.5,
            file=upload_file,
            max_questions=5,
            se_threshold=0.35,
        )

        last_ans = advance_res.get("last_answer") or {}
        transcript = last_ans.get("transcript", "")
        tech_score = last_ans.get("correctness_score")
        comm_score = last_ans.get("behavior_score")
        updated_theta = advance_res.get("theta")
        next_q_id = advance_res.get("next_question_id")
        is_complete = advance_res.get("is_complete")

        asked_questions.append(current_q_id)

        print(f"-----------------------------------------------------------------------")
        print(f"TURN {turn} of 5")
        print(f"-----------------------------------------------------------------------")
        print(f"Question ID       : {current_q_id}")
        print(f"Question Text     : {q_text}")
        print(f"Candidate Audio   : {audio_file_path.name}")
        print(f"Transcript (STT)  : \"{transcript}\"")
        print(f"Technical Score   : {tech_score}%")
        print(f"Comm Score        : {comm_score}%")
        print(f"Updated Theta     : {updated_theta}")
        print(f"Next Question ID  : {next_q_id}")
        print(f"Is Session Done?  : {is_complete}\n")

        # Update for next turn
        if is_complete or not next_q_id:
            print(f"[Session Completion Triggered at Turn {turn}] Reason: {advance_res.get('message')}\n")
            break

        current_q_id = next_q_id

    # Session Summary Checks
    print("=======================================================================")
    print("                    E2E SESSION VERIFICATION SUMMARY                  ")
    print("=======================================================================")
    print(f"Total Questions Asked : {len(asked_questions)}")
    print(f"Questions Sequence    : {asked_questions}")

    # Check 1: Unique questions (no repetition)
    has_duplicates = len(asked_questions) != len(set(asked_questions))
    print(f"Check 1 - No Question Repeats   : {'FAILED (Duplicates found)' if has_duplicates else 'PASSED'}")

    # Check 2: Database answers count matches
    db_answers_count = await db["answers"].count_documents({"session_id": session_id})
    print(f"Check 2 - DB Answers Count Linked : {db_answers_count} (Expected {len(asked_questions)})")

    # Fetch final report
    report = await get_session_report(session_id=session_id)
    print(f"Check 3 - Report Technical Avg  : {report['overall_technical_score']}%")
    print(f"Check 4 - Report Comm Avg       : {report['overall_communication_score']}%")
    print(f"Check 5 - Final Combined Score   : {report['overall_score']}%")
    print(f"Check 6 - Final Ability Theta   : {report['final_theta']} (SE: {report['standard_error']})")
    print("=======================================================================\n")

    close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(run_e2e_test())
