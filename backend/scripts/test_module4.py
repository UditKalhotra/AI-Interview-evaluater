"""
Module 4 Verification Script.
Tests STT transcription service and submit-answer endpoint handling audio upload and MongoDB record creation.
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
from app.services.stt import transcribe_audio, _estimate_word_timestamps


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
    print("--- 1. Testing STT Service ---")
    dummy_wav_path = os.path.join(backend_dir, "uploads", "test_sample.wav")
    os.makedirs(os.path.dirname(dummy_wav_path), exist_ok=True)
    create_dummy_wav(dummy_wav_path)

    res = await transcribe_audio(dummy_wav_path)
    print("STT Result:", res)
    assert "transcript" in res, "Missing 'transcript' key in STT result"
    assert "words" in res, "Missing 'words' key in STT result"
    print("[PASS] STT service test passed successfully!")

    print("--- 2. Testing Word Timestamps Estimation ---")
    sample_text = "This is a test answer for technical interview evaluation."
    words = _estimate_word_timestamps(sample_text)
    assert len(words) == len(sample_text.split())
    print("Estimated words count:", len(words))
    print("[PASS] Word timestamp estimation test passed!")

    print("--- 3. Testing POST /interview/submit-answer FastAPI Endpoint ---")
    with TestClient(app) as client:
        with open(dummy_wav_path, "rb") as f:
            response = client.post(
                "/interview/submit-answer",
                data={
                    "session_id": "test_session_m4",
                    "question_id": "MOHLER_1_1",
                    "response_time_seconds": "3.45",
                },
                files={"file": ("test_sample.wav", f, "audio/wav")},
            )
        print("Submit endpoint status code:", response.status_code)
        print("Submit endpoint response:", response.json())
        assert response.status_code == 200, f"Submit endpoint failed: {response.text}"
        json_data = response.json()
        assert "answer_id" in json_data
        assert json_data["session_id"] == "test_session_m4"
        assert json_data["question_id"] == "MOHLER_1_1"
        assert json_data["response_time_seconds"] == 3.45
        assert "audio_url" in json_data
        assert "transcript" in json_data
        print("[PASS] Submit-answer endpoint test passed successfully!")

    print("\n--- Module 4 Verification Summary ---")
    print("ALL TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(main())
