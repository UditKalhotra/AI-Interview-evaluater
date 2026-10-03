"""
Module 10 Verification Script.

Tests Report Generation logic:
1. Orchestrates / sets up a 5-question mock interview session in MongoDB using TestClient.
2. Invokes GET /interview/session/{session_id}/report endpoint to generate and return the report.
3. Verifies technical score, communication score, theta ability, per-question breakdown table,
   per-topic score breakdown, chart-ready data structure, and strengths/weaknesses generation.
4. Verifies MongoDB 'reports' collection caching behavior and refresh parameter.
5. Verifies 404 behavior for invalid session IDs.
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
    print("--- 1. Initializing Module 10 Test Session ---")

    session_id = "test_session_m10_e2e"
    dummy_wav_path = os.path.join(backend_dir, "uploads", "test_sample_m10.wav")
    os.makedirs(os.path.dirname(dummy_wav_path), exist_ok=True)
    create_dummy_wav(dummy_wav_path)

    with TestClient(app) as client:
        # Step 1: Start session and run 5 mock interview turns
        start_resp = client.post("/interview/session/start", data={"session_id": session_id})
        assert start_resp.status_code == 200, f"Start session failed: {start_resp.text}"
        start_data = start_resp.json()
        current_question_id = start_data.get("current_question_id") or "MOHLER_1_1"

        print(f"Session {session_id} initialized with initial question: {current_question_id}")

        turn = 1
        max_turns = 5
        is_complete = False

        while not is_complete and turn <= max_turns:
            with open(dummy_wav_path, "rb") as f:
                adv_resp = client.post(
                    f"/interview/session/{session_id}/advance",
                    data={
                        "question_id": current_question_id,
                        "response_time_seconds": "2.10",
                        "max_questions": "5",
                        "se_threshold": "0.35",
                    },
                    files={"file": (f"turn_{turn}.wav", f, "audio/wav")},
                )
            assert adv_resp.status_code == 200, f"Advance failed on turn {turn}: {adv_resp.text}"
            adv_data = adv_resp.json()
            is_complete = adv_data.get("is_complete", False)
            if not is_complete:
                current_question_id = adv_data.get("next_question_id")
            turn += 1

        print(f"Completed {turn - 1} turn mock interview. Session complete = {is_complete}")

        # Step 2: Test Report Generation via GET /interview/session/{session_id}/report
        print("\n--- 2. Testing Report Generation Endpoint ---")
        report_resp = client.get(f"/interview/session/{session_id}/report?refresh=true")
        assert report_resp.status_code == 200, f"Report generation endpoint failed: {report_resp.text}"
        report_data = report_resp.json()

        assert report_data["session_id"] == session_id
        assert "overall_technical_score" in report_data
        assert "overall_communication_score" in report_data
        assert "overall_score" in report_data
        assert "final_theta" in report_data
        assert "standard_error" in report_data
        assert "per_question_breakdown" in report_data
        assert "topic_breakdown" in report_data
        assert "chart_data" in report_data
        assert "strengths" in report_data
        assert "weaknesses" in report_data

        print(f"Overall Technical Score: {report_data['overall_technical_score']}%")
        print(f"Overall Communication Score: {report_data['overall_communication_score']}%")
        print(f"Overall Combined Score: {report_data['overall_score']}%")
        print(f"Final Theta: {report_data['final_theta']} (SE: {report_data['standard_error']})")
        print(f"Total Questions Answered: {report_data['total_questions_answered']}")

        # Verify Per-Question Breakdown contents
        pq = report_data["per_question_breakdown"]
        assert len(pq) == 5, f"Expected 5 questions in breakdown, got {len(pq)}"
        for item in pq:
            assert "question_id" in item
            assert "question_text" in item
            assert "topic" in item
            assert "correctness_score" in item
            assert "behavior_score" in item
            assert "missed_rubric_points" in item

        print(f"[PASS] Per-question breakdown verified ({len(pq)} questions).")

        # Verify Topic Breakdown contents
        tb = report_data["topic_breakdown"]
        assert len(tb) > 0, "Expected non-empty topic breakdown"
        for t in tb:
            assert "topic" in t
            assert "avg_correctness_score" in t
            assert "avg_behavior_score" in t
            assert "avg_combined_score" in t
        print(f"[PASS] Topic breakdown verified ({len(tb)} topics).")

        # Verify Chart Data structure
        cd = report_data["chart_data"]
        assert "topics" in cd
        assert "technical_scores" in cd
        assert "communication_scores" in cd
        assert "combined_scores" in cd
        assert "score_breakdown_by_topic" in cd
        print("[PASS] Chart-ready data structure verified successfully.")

        # Verify Strengths and Weaknesses
        strengths = report_data["strengths"]
        weaknesses = report_data["weaknesses"]
        assert 2 <= len(strengths) <= 3, f"Expected 2-3 strengths, got {len(strengths)}"
        assert 2 <= len(weaknesses) <= 3, f"Expected 2-3 weaknesses, got {len(weaknesses)}"

        print("Strengths:")
        for s in strengths:
            print(f"  + {s}")
        print("Weaknesses:")
        for w in weaknesses:
            print(f"  - {w}")

        print("[PASS] Strengths and weaknesses auto-generation verified.")

        # Step 3: Test Caching (subsequent call without refresh=true returns same cached payload)
        print("\n--- 3. Testing Caching Behavior ---")
        cached_resp = client.get(f"/interview/session/{session_id}/report")
        assert cached_resp.status_code == 200
        cached_data = cached_resp.json()
        assert cached_data["session_id"] == session_id
        assert cached_data["overall_technical_score"] == report_data["overall_technical_score"]
        print("[PASS] Report caching verified successfully.")

        # Step 4: Test 404 for Invalid Session ID
        print("\n--- 4. Testing 404 for Invalid Session ID ---")
        err_resp = client.get("/interview/session/non_existent_session_99999/report")
        assert err_resp.status_code == 404, f"Expected 404, got {err_resp.status_code}"
        print("[PASS] 404 error handling verified for non-existent sessions.")

    print("\n--- Module 10 Verification Summary ---")
    print("ALL MODULE 10 TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
