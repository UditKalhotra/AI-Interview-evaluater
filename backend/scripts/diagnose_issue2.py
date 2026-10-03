"""
Diagnosis script for Issue 2:
Queries score_results documents and prints features, behavior_score, and is_fallback.
Also checks environment loading and GEMINI_API_KEY.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv(os.path.join(backend_dir, ".env"))

from app.db import get_database, connect_to_mongo


async def main():
    connect_to_mongo()
    db = get_database()

    print("=== Diagnosing Issue 2 ===")
    gemini_key = os.getenv("GEMINI_API_KEY")
    print(f"GEMINI_API_KEY loaded: {'YES (len=' + str(len(gemini_key)) + ')' if gemini_key else 'NO (empty or None)'}")

    cursor = db["score_results"].find({}).sort("_id", -1).limit(10)
    score_docs = await cursor.to_list(length=10)

    print(f"\nQueried {len(score_docs)} recent score_results documents:\n")

    fallback_count = 0
    non_fallback_count = 0

    for idx, doc in enumerate(score_docs, 1):
        answer_id = doc.get("answer_id")
        behavior_score = doc.get("behavior_score")
        is_fallback = doc.get("is_fallback")
        features = doc.get("features")
        explanation = doc.get("behavior_explanation") or doc.get("explanation")

        if is_fallback is True:
            fallback_count += 1
        elif is_fallback is False:
            non_fallback_count += 1

        print(f"[{idx}] Answer ID: {answer_id}")
        print(f"    Behavior Score: {behavior_score}")
        print(f"    Is Fallback: {is_fallback}")
        print(f"    Features: {features}")
        print(f"    Explanation: {explanation[:100] if explanation else None}")
        print("-" * 60)

    print(f"\nSummary: Total={len(score_docs)}, Fallbacks={fallback_count}, Non-Fallbacks={non_fallback_count}")


if __name__ == "__main__":
    asyncio.run(main())
