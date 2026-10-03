"""
Reproducible Scoring Test Script for Technical Evaluation Pipeline.

Tests four distinct candidate answer cases against the exact same production
scoring function (`score_correctness` in app.services.scoring):

Case A — Clearly correct answer
Case B — Partially correct answer
Case C — Clearly incorrect answer
Case D — Unrelated answer

Prints:
- Question
- Reference answer
- Candidate answer
- LSA similarity score
- Rubric coverage score
- Final technical/correctness score
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.scoring import score_correctness


def run_scoring_tests():
    question_text = "What is the role of a prototype program in problem solving?"
    reference_answer = "To simulate the behaviour of portions of the desired software product."
    rubric = [
        "1. Simulates portions of software product",
        "2. Identifies early design issues or specifications",
        "3. Provides a preliminary model before full implementation"
    ]

    test_cases = [
        {
            "label": "Case A — Clearly Correct Answer",
            "candidate_answer": (
                "A prototype program is designed to simulate the behavior of portions of the desired software product. "
                "It allows engineers to test early design specifications and catch requirements before final development."
            ),
        },
        {
            "label": "Case B — Partially Correct Answer",
            "candidate_answer": (
                "It is a basic preliminary model used to test some initial software features during problem solving."
            ),
        },
        {
            "label": "Case C — Clearly Incorrect Answer",
            "candidate_answer": (
                "A prototype is a network switch hardware device used to transmit internet data packets across routers."
            ),
        },
        {
            "label": "Case D — Unrelated Answer",
            "candidate_answer": (
                "I enjoy going for long walks in the park and eating pepperoni pizza on Friday nights."
            ),
        },
    ]

    print("\n=======================================================================")
    print("        PRODUCTION TECHNICAL LSA & RUBRIC SCORING PIPELINE TEST       ")
    print("=======================================================================")
    print(f"QUESTION         : {question_text}")
    print(f"REFERENCE ANSWER : {reference_answer}")
    print(f"RUBRIC POINTS    : {rubric}")
    print("-----------------------------------------------------------------------\n")

    for test in test_cases:
        label = test["label"]
        cand = test["candidate_answer"]

        # Call production scoring function
        result = score_correctness(cand, reference_answer, rubric)

        print(f"=== {label} ===")
        print(f"Candidate Answer       : \"{cand}\"")
        print(f"LSA Similarity Score   : {result['lsa_similarity_score']:.1f}%")
        print(f"Rubric Coverage Score  : {result['rubric_coverage_score']:.1f}% ({result['matched_rubric_points']}/{result['total_rubric_points']} points matched)")
        print(f"Final Technical Score  : {result['correctness_score']:.1f}%")
        print("-----------------------------------------------------------------------\n")


if __name__ == "__main__":
    run_scoring_tests()
