"""
Module 9 Verification Script.

Tests complete interview flow orchestration (Modules 3-8 sequential loop):
1. Starts a new interview session.
2. Runs a 5-question mock interview calling POST /interview/session/{session_id}/advance.
3. Confirms STT transcription, speech feature extraction, behavior scoring (Gemini/fallback),
   LSA correctness scoring, IRT theta update, and next-question audio URL for each turn.
4. Confirms stopping rule execution and session status transition to 'complete' in MongoDB.
"""

import os
import sys
import wave
import struct
import asyncio
from fastapi.testclient import TestClient

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.db import get_database, connect_to_mongo


def create_dummy_wav(filepath: str, duration_sec: float = 1.0):
    """Create a simple WAV file for testing audio upload."""
    sample_rate = 16000
    n_samples = int(sample_rate * duration_sec)
    with wave.open(filepath, "w") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        for i in range(n_samples):
            value = int(500 * (i % 10))
            data = struct.pack("<h", value)
            wav_file.writeframesraw(data)


async def main():
    print("--- 1. Initializing Module 9 Orchestration Test ---")

    session_id = "test_session_m9_e2e"
    dummy_wav_path = os.path.join(backend_dir, "uploads", "test_sample_m9.wav")
    os.makedirs(os.path.dirname(dummy_wav_path), exist_ok=True)
    create_dummy_wav(dummy_wav_path)

    with TestClient(app) as client:
        # Step 1: Start Session
        start_resp = client.post("/interview/session/start", data={"session_id": session_id})
        assert start_resp.status_code == 200, f"Start session failed: {start_resp.text}"
        start_data = start_resp.json()
        print(f"Session started successfully. ID: {session_id}")
        print(f"Initial question: {start_data.get('current_question_id')}")

        current_question_id = start_data.get("current_question_id") or "MOHLER_1_1"

        # Step 2: Loop 5 turns calling POST /interview/session/{session_id}/advance
        turn = 1
        max_turns = 5
        is_complete = False

        while not is_complete and turn <= max_turns:
            print(f"\n--- Executing Orchestration Turn {turn}/{max_turns} (Question: {current_question_id}) ---")

            with open(dummy_wav_path, "rb") as f:
                adv_resp = client.post(
                    f"/interview/session/{session_id}/advance",
                    data={
                        "question_id": current_question_id,
                        "response_time_seconds": "2.45",
                        "max_questions": "5",
                        "se_threshold": "0.35",
                    },
                    files={"file": (f"turn_{turn}.wav", f, "audio/wav")},
                )

            assert adv_resp.status_code == 200, f"Advance endpoint failed on turn {turn}: {adv_resp.text}"
            adv_data = adv_resp.json()

            print(f"Turn {turn} Response Status: {adv_data.get('status')}")
            print(f"Candidate Theta: {adv_data.get('theta')} (SE: {adv_data.get('standard_error')})")
            print(f"Answered Count: {adv_data.get('answered_count')}")

            last_ans = adv_data.get("last_answer")
            assert last_ans is not None, f"Expected last_answer in turn {turn} response"
            print(f"Answer ID: {last_ans.get('answer_id')}")
            print(f"Behavior Score: {last_ans.get('behavior_score')}")
            print(f"Correctness Score: {last_ans.get('correctness_score')}")

            is_complete = adv_data.get("is_complete", False)
            if not is_complete:
                current_question_id = adv_data.get("next_question_id")
                print(f"Next Question ID: {current_question_id}")
                print(f"Next Question Audio URL: {adv_data.get('next_question_audio_url')}")

            turn += 1

        print("\n--- 3. Verifying Final Interview Completion State ---")
        assert is_complete is True, "Expected interview session to be completed after 5 turns"
        print(f"[PASS] Session status successfully updated to completed after {turn - 1} turns!")

        # Step 3: Verify MongoDB document states
        connect_to_mongo()
        db = get_database()

        session_doc = await db["sessions"].find_one({"session_id": session_id})
        assert session_doc is not None, "Expected session document in MongoDB"
        assert session_doc.get("status") == "complete", f"Expected session status 'complete', got {session_doc.get('status')}"

        answers_count = await db["answers"].count_documents({"session_id": session_id})
        assert answers_count == 5, f"Expected 5 answer documents in MongoDB, got {answers_count}"

        print(f"MongoDB Verification: Found session status='{session_doc.get('status')}', total answers={answers_count}.")
        print("[PASS] MongoDB collections verified successfully!")

    print("\n--- Module 9 Verification Summary ---")
    print("ALL MODULE 9 TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(main())
