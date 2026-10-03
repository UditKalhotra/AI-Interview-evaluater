"""
Module 5 Verification Script.
Tests speech feature extraction service and GET /interview/answer/{answer_id}/features endpoint.
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
from app.services.features import (
    extract_features,
    _count_fillers,
    _analyze_pauses,
    _calculate_speaking_rate,
    _count_repetitions,
    _check_asked_repeat,
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
    print("--- 1. Testing Unit Functions in features.py ---")
    sample_transcript = "Um, uh, basically I think that, you know, python is fast. Python is is cool. Could you repeat the question?"
    sample_words = [
        {"word": "Um,", "start": 0.0, "end": 0.3},
        {"word": "uh,", "start": 0.4, "end": 0.6},
        {"word": "basically", "start": 1.2, "end": 1.7},  # gap 0.6s (pause)
        {"word": "I", "start": 1.8, "end": 1.9},
        {"word": "think", "start": 2.0, "end": 2.3},
        {"word": "that,", "start": 2.4, "end": 2.6},
        {"word": "you", "start": 4.5, "end": 4.7},  # gap 1.9s (long pause)
        {"word": "know,", "start": 4.8, "end": 5.0},
        {"word": "python", "start": 5.1, "end": 5.5},
        {"word": "is", "start": 5.6, "end": 5.8},
        {"word": "fast.", "start": 5.9, "end": 6.2},
        {"word": "Python", "start": 6.3, "end": 6.7},
        {"word": "is", "start": 6.8, "end": 7.0},
        {"word": "is", "start": 7.1, "end": 7.3},
        {"word": "cool.", "start": 7.4, "end": 7.6},
        {"word": "Could", "start": 7.7, "end": 7.9},
        {"word": "you", "start": 8.0, "end": 8.1},
        {"word": "repeat", "start": 8.2, "end": 8.5},
        {"word": "the", "start": 8.6, "end": 8.7},
        {"word": "question?", "start": 8.8, "end": 9.2},
    ]

    fillers = _count_fillers(sample_transcript)
    print(f"Fillers count: {fillers}")
    assert fillers >= 3, f"Expected fillers >= 3, got {fillers}"

    pauses = _analyze_pauses(sample_words)
    print(f"Pauses analysis: {pauses}")
    assert pauses["count"] == 2, f"Expected 2 pauses, got {pauses['count']}"
    assert pauses["long_pauses_count"] == 1, f"Expected 1 long pause, got {pauses['long_pauses_count']}"

    wpm = _calculate_speaking_rate(sample_transcript, sample_words)
    print(f"Speaking rate WPM: {wpm}")
    assert wpm > 0, f"Expected positive WPM, got {wpm}"

    reps = _count_repetitions(sample_transcript)
    print(f"Repetitions count: {reps}")
    assert reps >= 1, f"Expected repetition count >= 1 (e.g. 'is is'), got {reps}"

    asked_repeat = _check_asked_repeat(sample_transcript)
    print(f"Asked repeat flag: {asked_repeat}")
    assert asked_repeat is True, f"Expected asked_repeat=True, got {asked_repeat}"

    extracted = extract_features("dummy.wav", sample_transcript, sample_words)
    print("Full extracted dict:", extracted)
    assert "fillers" in extracted
    assert "pauses" in extracted
    assert "speaking_rate" in extracted
    assert "repetitions" in extracted
    assert "asked_repeat" in extracted
    print("[PASS] Unit feature extraction tests passed successfully!")

    print("\n--- 2. Testing POST submit-answer & GET answer/{answer_id}/features Endpoints ---")
    dummy_wav_path = os.path.join(backend_dir, "uploads", "test_sample_m5.wav")
    os.makedirs(os.path.dirname(dummy_wav_path), exist_ok=True)
    create_dummy_wav(dummy_wav_path)

    with TestClient(app) as client:
        with open(dummy_wav_path, "rb") as f:
            submit_resp = client.post(
                "/interview/submit-answer",
                data={
                    "session_id": "test_session_m5",
                    "question_id": "MOHLER_1_1",
                    "response_time_seconds": "2.10",
                },
                files={"file": ("test_sample_m5.wav", f, "audio/wav")},
            )

        assert submit_resp.status_code == 200, f"Submit failed: {submit_resp.text}"
        submit_data = submit_resp.json()
        answer_id = submit_data["answer_id"]
        print(f"Answer submitted successfully. answer_id: {answer_id}")

        features_resp = client.get(f"/interview/answer/{answer_id}/features")
        print("GET features status code:", features_resp.status_code)
        print("GET features response:", features_resp.json())

        assert features_resp.status_code == 200, f"Features GET failed: {features_resp.text}"
        features_json = features_resp.json()
        assert features_json["answer_id"] == answer_id
        assert "features" in features_json
        feat = features_json["features"]
        assert "fillers" in feat
        assert "pauses" in feat
        assert "speaking_rate" in feat
        assert "repetitions" in feat
        assert "asked_repeat" in feat
        print("[PASS] GET /interview/answer/{answer_id}/features endpoint test passed!")

    print("\n--- Module 5 Verification Summary ---")
    print("ALL MODULE 5 TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(main())
