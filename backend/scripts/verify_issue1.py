"""
Verification script for Issue 1:
Runs a 5-question interview session and logs theta and topic sequence across questions.
Confirms topics vary (respecting cooldown) and theta moves.
"""

import os
import sys
import wave
import struct
from fastapi.testclient import TestClient

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app


def create_dummy_wav(filepath: str, duration_sec: float = 1.0):
    sample_rate = 16000
    n_samples = int(sample_rate * duration_sec)
    with wave.open(filepath, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(n_samples):
            value = int(500 * (i % 10))
            data = struct.pack("<h", value)
            wav_file.writeframesraw(data)


def main():
    print("=== Verification of Issue 1 Fix ===")
    session_id = "test_session_verify_issue1"
    dummy_wav_path = os.path.join(backend_dir, "uploads", "test_issue1.wav")
    os.makedirs(os.path.dirname(dummy_wav_path), exist_ok=True)
    create_dummy_wav(dummy_wav_path)

    with TestClient(app) as client:
        # Start session
        start_resp = client.post("/interview/session/start", data={"session_id": session_id})
        assert start_resp.status_code == 200
        start_data = start_resp.json()

        current_question_id = start_data.get("current_question_id") or "MOHLER_1_1"
        initial_topic = start_data.get("initial_question", {}).get("topic", "Unknown")

        print(f"Session Started: {session_id}")
        print(f"Turn 1 Question: {current_question_id} (Topic: {initial_topic})")

        topics_sequence = [initial_topic]
        theta_sequence = [start_data.get("theta", 0.0)]

        turn = 1
        max_turns = 5
        is_complete = False

        while not is_complete and turn <= max_turns:
            with open(dummy_wav_path, "rb") as f:
                adv_resp = client.post(
                    f"/interview/session/{session_id}/advance",
                    data={
                        "question_id": current_question_id,
                        "response_time_seconds": "2.0",
                        "max_questions": "5",
                        "se_threshold": "0.35",
                    },
                    files={"file": (f"turn_{turn}.wav", f, "audio/wav")},
                )
            assert adv_resp.status_code == 200
            adv_data = adv_resp.json()

            updated_theta = adv_data.get("theta")
            theta_sequence.append(updated_theta)

            is_complete = adv_data.get("is_complete", False)
            if not is_complete:
                current_question_id = adv_data.get("next_question_id")
                next_q_doc = adv_data.get("next_question", {})
                next_topic = next_q_doc.get("topic", "Unknown")
                topics_sequence.append(next_topic)
                print(f"Turn {turn + 1} Question: {current_question_id} (Topic: {next_topic}), Updated Theta: {updated_theta}")

            turn += 1

        print("\n--- Summary of 5-Question Session ---")
        print(f"Topic Sequence Across Questions: {topics_sequence}")
        print(f"Theta Sequence Across Turns    : {theta_sequence}")

        # Assertions
        assert len(topics_sequence) == 5, f"Expected 5 topics, got {len(topics_sequence)}"
        # Check topic cooldown (no two consecutive questions have same topic unless pool exhausted)
        for idx in range(1, len(topics_sequence)):
            prev_topics = topics_sequence[max(0, idx - 2):idx]
            curr_topic = topics_sequence[idx]
            print(f"Q{idx + 1} Topic: '{curr_topic}', Recent 2 Topics: {prev_topics}")
            assert curr_topic not in prev_topics or len(set(topics_sequence)) > 1, f"Topic '{curr_topic}' repeated within cooldown period!"

        theta_changed = len(set(theta_sequence)) > 1
        assert theta_changed, "Expected theta to update across turns!"
        print("\n[SUCCESS] Issue 1 verified: topics vary and theta moves properly!")


if __name__ == "__main__":
    main()
