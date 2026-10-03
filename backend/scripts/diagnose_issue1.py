"""
Diagnosis script for Issue 1: ID format matching and theta progression test.
"""
import os
import sys
import asyncio

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db import get_database, connect_to_mongo


async def main():
    connect_to_mongo()
    db = get_database()

    print("--- Inspecting answers vs score_results ID formats ---")
    
    answers = await db["answers"].find({}).to_list(length=100)
    score_results = await db["score_results"].find({}).to_list(length=100)

    print(f"Total answers in DB: {len(answers)}")
    print(f"Total score_results in DB: {len(score_results)}")

    match_count = 0
    miss_count = 0

    for ans in answers:
        ans_id_str = str(ans["_id"])
        score_doc = await db["score_results"].find_one({
            "$or": [
                {"answer_id": ans_id_str},
                {"answer_id": ans["_id"]}
            ]
        })
        if score_doc:
            match_count += 1
            print(f"Answer {ans_id_str} matched score_result. Correctness: {score_doc.get('correctness_score')}, Behavior: {score_doc.get('behavior_score')}")
        else:
            miss_count += 1
            print(f"Answer {ans_id_str} MISSING in score_results!")

    print(f"\nSummary: Matches: {match_count}, Misses: {miss_count}")


if __name__ == "__main__":
    asyncio.run(main())
