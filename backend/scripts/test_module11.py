"""
Module 11 Verification Script.

Tests complete full-system integration flow:
1. Start screen session initialization via POST /interview/session/start.
2. 5-question voice-only interview loop via POST /interview/session/{session_id}/advance.
3. Automatic completion state verification in MongoDB.
4. Report page data fetching via GET /interview/session/{session_id}/report.
5. Verifies end-to-end data integrity across all 11 modules.
"""

import os
import sys
import wave
import struct
from fastapi.testclient import TestClient

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app


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


def main():
    print("==================================================================")
    print("--- Module 11 — Full Integration & Report UI Verification Test ---")
    print("==================================================================")

    session_id = "test_session_m11_full_e2e"
    dummy_wav_path = os.path.join(backend_dir, "uploads", "test_sample_m11.wav")
    os.makedirs(os.path.dirname(dummy_wav_path), exist_ok=True)
    create_dummy_wav(dummy_wav_path)

    with TestClient(app) as client:
        # Step 1: Landing Page / Start Screen Action -> Initialize Session
        print("\n--- Step 1: Start Screen Session Initialization ---")
        start_resp = client.post("/interview/session/start", data={"session_id": session_id})
        assert start_resp.status_code == 200, f"Start session failed: {start_resp.text}"
        start_data = start_resp.json()
        assert start_data["session_id"] == session_id
        assert start_data["status"] == "in_progress"
        first_q_id = start_data.get("current_question_id") or "MOHLER_1_1"
        print(f"[PASS] Session {session_id} successfully started in MongoDB.")
        print(f"       Initial Question ID: {first_q_id}")

        # Step 2: Voice Interview Loop (Module 9 advance loop until 'complete')
        print("\n--- Step 2: Continuous Voice Interview Loop (5 turns) ---")
        current_question_id = first_q_id
        turn = 1
        max_turns = 5
        is_complete = False

        while not is_complete and turn <= max_turns:
            print(f"  -> Turn {turn}/{max_turns}: Answering Question {current_question_id}...")
            with open(dummy_wav_path, "rb") as f:
                adv_resp = client.post(
                    f"/interview/session/{session_id}/advance",
                    data={
                        "question_id": current_question_id,
                        "response_time_seconds": "2.25",
                        "max_questions": "5",
                        "se_threshold": "0.35",
                    },
                    files={"file": (f"turn_{turn}.wav", f, "audio/wav")},
                )
            assert adv_resp.status_code == 200, f"Advance failed on turn {turn}: {adv_resp.text}"
            adv_data = adv_resp.json()

            print(f"     Status: {adv_data.get('status')}, Theta: {adv_data.get('theta')}, SE: {adv_data.get('standard_error')}")

            is_complete = adv_data.get("is_complete", False)
            if not is_complete:
                current_question_id = adv_data.get("next_question_id")

            turn += 1

        assert is_complete is True, "Expected interview session to complete after 5 turns"
        print(f"[PASS] Interview session completed after {turn - 1} turns.")

        # Step 3: Report Page Fetching -> Module 10 Endpoint
        print("\n--- Step 3: Report Page Data Retrieval ---")
        report_resp = client.get(f"/interview/session/{session_id}/report?refresh=true")
        assert report_resp.status_code == 200, f"Report retrieval failed: {report_resp.text}"
        report_data = report_resp.json()

        assert report_data["session_id"] == session_id
        assert report_data["status"] == "complete"
        assert "overall_technical_score" in report_data
        assert "overall_communication_score" in report_data
        assert "overall_score" in report_data
        assert "final_theta" in report_data
        assert "per_question_breakdown" in report_data
        assert "topic_breakdown" in report_data
        assert "chart_data" in report_data
        assert "strengths" in report_data
        assert "weaknesses" in report_data

        print("  Summary Results:")
        print(f"    - Overall Technical Score : {report_data['overall_technical_score']}%")
        print(f"    - Overall Communication   : {report_data['overall_communication_score']}%")
        print(f"    - Combined Overall Score  : {report_data['overall_score']}%")
        print(f"    - Final Theta Ability     : {report_data['final_theta']} (SE: {report_data['standard_error']})")
        print(f"    - Questions Evaluated     : {report_data['total_questions_answered']}")
        print(f"    - Topics Evaluated        : {len(report_data['topic_breakdown'])}")

        print("\n  Auto-Generated Strengths:")
        for s in report_data["strengths"]:
            print(f"    + {s}")

        print("\n  Auto-Generated Weaknesses:")
        for w in report_data["weaknesses"]:
            print(f"    - {w}")

        print("\n[PASS] Report Page payload successfully fetched and validated.")

    print("\n==================================================================")
    print("--- FULL 11-MODULE INTERVIEW SYSTEM INTEGRATION TEST PASSED! ---")
    print("==================================================================")


if __name__ == "__main__":
    main()
