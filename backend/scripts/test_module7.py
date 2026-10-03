"""
Module 7 Verification Script.
Tests LSA content evaluation pipeline (Phase A model load, Phase B scoring function,
and GET /interview/answer/{answer_id}/correctness-score endpoint).
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
from app.services.scoring import (
    compute_lsa_similarity,
    evaluate_rubric,
    score_correctness,
    score_answer_correctness,
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
    print("--- 1. Testing LSA Cosine Similarity Function ---")

    ref = "To simulate the behaviour of portions of the desired software product."
    strong_ans = "A prototype simulates the behaviors of portions of the desired software product to test features."
    weak_ans = "I do not know the answer to this question."

    sim_strong = compute_lsa_similarity(strong_ans, ref)
    sim_weak = compute_lsa_similarity(weak_ans, ref)

    print(f"Similarity (Strong Candidate Answer): {sim_strong:.4f}")
    print(f"Similarity (Weak Candidate Answer)  : {sim_weak:.4f}")

    assert sim_strong > sim_weak, f"Expected sim_strong > sim_weak, got {sim_strong} <= {sim_weak}"
    print("[PASS] LSA cosine similarity logic passed successfully!")

    print("\n--- 2. Testing Rubric Evaluation & Score Correctness ---")
    rubric = [
        "1. To simulate the behaviour of portions of software",
        "2. Allow error checking and prototyping",
        "3. Provide early feedback for project estimations",
    ]

    scoring_res = score_correctness(strong_ans, ref, rubric)
    print("Score correctness output:", scoring_res)

    assert "correctness_score" in scoring_res
    assert "lsa_similarity_score" in scoring_res
    assert "rubric_coverage_score" in scoring_res
    assert "matched_rubric_points" in scoring_res
    assert 0.0 <= scoring_res["correctness_score"] <= 100.0
    print("[PASS] Rubric evaluation & score correctness logic passed successfully!")

    print("\n--- 3. Testing GET /interview/answer/{answer_id}/correctness-score Endpoint ---")
    dummy_wav_path = os.path.join(backend_dir, "uploads", "test_sample_m7.wav")
    os.makedirs(os.path.dirname(dummy_wav_path), exist_ok=True)
    create_dummy_wav(dummy_wav_path)

    with TestClient(app) as client:
        with open(dummy_wav_path, "rb") as f:
            submit_resp = client.post(
                "/interview/submit-answer",
                data={
                    "session_id": "test_session_m7",
                    "question_id": "MOHLER_1_1",
                    "response_time_seconds": "2.50",
                },
                files={"file": ("test_sample_m7.wav", f, "audio/wav")},
            )

        assert submit_resp.status_code == 200, f"Submit answer failed: {submit_resp.text}"
        answer_id = submit_resp.json()["answer_id"]
        print(f"Answer submitted successfully. answer_id: {answer_id}")

        corr_resp = client.get(f"/interview/answer/{answer_id}/correctness-score")
        print("GET correctness-score status code:", corr_resp.status_code)
        print("GET correctness-score response:", corr_resp.json())

        assert corr_resp.status_code == 200, f"Correctness score GET failed: {corr_resp.text}"
        c_json = corr_resp.json()
        assert c_json["answer_id"] == answer_id
        assert "correctness_score" in c_json
        assert "lsa_similarity_score" in c_json
        assert "rubric_coverage_score" in c_json
        assert 0.0 <= c_json["correctness_score"] <= 100.0
        print("[PASS] GET /interview/answer/{answer_id}/correctness-score endpoint test passed!")

    print("\n--- Module 7 Verification Summary ---")
    print("ALL MODULE 7 TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(main())
