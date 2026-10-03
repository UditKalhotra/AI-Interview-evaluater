"""
Module 6 Verification Script.
Tests Gemini behavior/communication scoring service, fallback scoring algorithm,
and GET /interview/answer/{answer_id}/behavior-score endpoint.
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
from app.services.gemini import (
    compute_fallback_behavior_score,
    _parse_gemini_response,
    score_behavior,
    score_answer_behavior,
)


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
    print("--- 1. Testing Fallback Behavior Scoring Unit Logic ---")

    # Case A: Ideal candidate delivery
    ideal_features = {
        "fillers": 0,
        "pauses": {"count": 0, "total_duration_seconds": 0.0, "long_pauses_count": 0},
        "speaking_rate": 140.0,
        "repetitions": 0,
        "asked_repeat": False,
    }
    score_a = compute_fallback_behavior_score(ideal_features)
    print("Ideal candidate score:", score_a)
    assert score_a["behavior_score"] == 100.0, f"Expected 100.0, got {score_a['behavior_score']}"
    assert "is_fallback" in score_a and score_a["is_fallback"] is True

    # Case B: Heavy fillers and pauses
    flawed_features = {
        "fillers": 4,  # -12 pts
        "pauses": {"count": 3, "total_duration_seconds": 4.5, "long_pauses_count": 2},  # -6 + -10 = -16 pts
        "speaking_rate": 90.0,  # -5 pts
        "repetitions": 1,  # -4 pts
        "asked_repeat": True,  # -5 pts
    }
    score_b = compute_fallback_behavior_score(flawed_features)
    print("Flawed candidate score:", score_b)
    assert score_b["behavior_score"] < 100.0, f"Expected score < 100, got {score_b['behavior_score']}"
    assert 0.0 <= score_b["behavior_score"] <= 100.0

    print("[PASS] Unit fallback scoring logic passed successfully!")

    print("\n--- 2. Testing Gemini Response Parsing Helper ---")
    mock_gemini_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "```json\n{\n  \"behavior_score\": 88.5,\n  \"explanation\": \"Good articulation and pace with minimal hesitation.\"\n}\n```"
                        }
                    ]
                }
            }
        ]
    }
    parsed = _parse_gemini_response(mock_gemini_json)
    print("Parsed mock Gemini response:", parsed)
    assert parsed is not None
    assert parsed["behavior_score"] == 88.5
    assert "Good articulation" in parsed["explanation"]
    assert parsed["is_fallback"] is False
    print("[PASS] Gemini response parsing passed successfully!")

    print("\n--- 3. Testing score_behavior Function ---")
    score_res = await score_behavior(ideal_features)
    print("score_behavior result:", score_res)
    assert "behavior_score" in score_res
    assert "explanation" in score_res
    assert 0.0 <= score_res["behavior_score"] <= 100.0
    print("[PASS] score_behavior function passed successfully!")

    print("\n--- 4. Testing GET /interview/answer/{answer_id}/behavior-score Endpoint ---")
    dummy_wav_path = os.path.join(backend_dir, "uploads", "test_sample_m6.wav")
    os.makedirs(os.path.dirname(dummy_wav_path), exist_ok=True)
    create_dummy_wav(dummy_wav_path)

    with TestClient(app) as client:
        with open(dummy_wav_path, "rb") as f:
            submit_resp = client.post(
                "/interview/submit-answer",
                data={
                    "session_id": "test_session_m6",
                    "question_id": "MOHLER_1_1",
                    "response_time_seconds": "1.80",
                },
                files={"file": ("test_sample_m6.wav", f, "audio/wav")},
            )

        assert submit_resp.status_code == 200, f"Submit answer failed: {submit_resp.text}"
        answer_id = submit_resp.json()["answer_id"]
        print(f"Answer submitted successfully. answer_id: {answer_id}")

        behavior_resp = client.get(f"/interview/answer/{answer_id}/behavior-score")
        print("GET behavior-score status code:", behavior_resp.status_code)
        print("GET behavior-score response:", behavior_resp.json())

        assert behavior_resp.status_code == 200, f"Behavior score GET failed: {behavior_resp.text}"
        b_json = behavior_resp.json()
        assert b_json["answer_id"] == answer_id
        assert "behavior_score" in b_json
        assert "explanation" in b_json
        assert 0.0 <= b_json["behavior_score"] <= 100.0
        print("[PASS] GET /interview/answer/{answer_id}/behavior-score endpoint test passed!")

    print("\n--- Module 6 Verification Summary ---")
    print("ALL MODULE 6 TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(main())
