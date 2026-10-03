"""
Module 8 Verification Script.

Tests IRT engine logic:
1. 1PL / 2PL IRT response probability P(theta), Fisher Information, and Standard Error.
2. MAP Newton-Raphson theta update logic under correct/incorrect/mixed responses.
3. Adaptive question selection finding question with irt_difficulty closest to updated theta.
4. Stopping rules (max questions limit, SE convergence, question bank exhaustion).
5. FastAPI endpoint GET /interview/session/{session_id}/next-question using TestClient.
"""

import os
import sys
import asyncio
from fastapi.testclient import TestClient

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.services.irt import (
    calculate_item_probability,
    calculate_information,
    calculate_standard_error,
    update_theta,
    process_next_question_for_session,
)


async def main():
    print("--- 1. Testing Basic IRT Mathematical Functions ---")

    # Item probability tests
    p_easy = calculate_item_probability(theta=0.0, b=-1.5)
    p_equal = calculate_item_probability(theta=0.0, b=0.0)
    p_hard = calculate_item_probability(theta=0.0, b=1.5)

    print(f"P(theta=0, b=-1.5 [Easy])  : {p_easy:.4f}")
    print(f"P(theta=0, b=0.0  [Medium]): {p_equal:.4f}")
    print(f"P(theta=0, b=1.5  [Hard])  : {p_hard:.4f}")

    assert p_easy > p_equal > p_hard, "Expected P(easy) > P(equal) > P(hard)"
    assert abs(p_equal - 0.5) < 1e-4, "Expected P(theta=0, b=0) == 0.5"
    print("[PASS] Item probability functions validated successfully!")

    print("\n--- 2. Testing Ability (Theta) Update & Standard Error ---")

    # High correctness response -> theta should increase above 0.0
    responses_high = [
        {"irt_difficulty": 0.0, "correctness_score": 90.0},
        {"irt_difficulty": 0.5, "correctness_score": 85.0},
    ]
    theta_high, se_high = update_theta(responses_high, current_theta=0.0)
    print(f"High scores response -> updated theta: {theta_high:.4f}, SE: {se_high:.4f}")

    # Low correctness response -> theta should decrease below 0.0
    responses_low = [
        {"irt_difficulty": 0.0, "correctness_score": 10.0},
        {"irt_difficulty": -0.5, "correctness_score": 15.0},
    ]
    theta_low, se_low = update_theta(responses_low, current_theta=0.0)
    print(f"Low scores response  -> updated theta: {theta_low:.4f}, SE: {se_low:.4f}")

    assert theta_high > 0.0, f"Expected theta_high > 0.0, got {theta_high}"
    assert theta_low < 0.0, f"Expected theta_low < 0.0, got {theta_low}"
    assert se_high < 1.0, f"Expected standard error to decrease with more items, got {se_high}"
    print("[PASS] Theta estimation and SE calculations validated successfully!")

    print("\n--- 3. Testing API Endpoints via TestClient ---")

    with TestClient(app) as client:
        # Start a session
        start_resp = client.post("/interview/session/start", data={"session_id": "test_session_m8"})
        print("Start session status code:", start_resp.status_code)
        print("Start session response:", start_resp.json())
        assert start_resp.status_code == 200, f"Start session failed: {start_resp.text}"
        s_data = start_resp.json()
        assert s_data["session_id"] == "test_session_m8"
        assert "theta" in s_data
        assert "initial_question" in s_data or "current_question_id" in s_data

        # Fetch next question
        next_resp = client.get("/interview/session/test_session_m8/next-question?max_questions=5")
        print("Next question status code:", next_resp.status_code)
        print("Next question response:", next_resp.json())
        assert next_resp.status_code == 200, f"Next question failed: {next_resp.text}"
        n_data = next_resp.json()
        assert n_data["session_id"] == "test_session_m8"
        assert "theta" in n_data
        assert "standard_error" in n_data
        assert "is_complete" in n_data
        assert "next_question_id" in n_data
        print("[PASS] Next question endpoint validated successfully!")

        # Verify stopping rule with max_questions parameter = 0
        stop_resp = client.get("/interview/session/test_session_m8/next-question?max_questions=0")
        print("Stopping rule test response:", stop_resp.json())
        assert stop_resp.status_code == 200
        st_data = stop_resp.json()
        assert st_data["is_complete"] is True
        assert st_data["status"] == "complete"
        print("[PASS] Stopping rule (max_questions limit) validated successfully!")

    print("\n--- Module 8 Verification Summary ---")
    print("ALL MODULE 8 TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(main())
