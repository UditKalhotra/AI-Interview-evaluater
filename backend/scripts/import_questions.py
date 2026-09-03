"""
Module 2 — Question Bank Import (from Master Question Bank CSV).

Reads backend/data/Master_Question_Bank_with_topics_active.csv, skips any row
where `active` is False, parses the `rubric` column's numbered text into a
clean list of rubric-point strings, and upserts one document per remaining
row into MongoDB's `questions` collection using `question_id` as the unique
key (safe to re-run).

This script is offline — it does not touch Data.csv (Mohler), which is
reserved exclusively for Module 7's scoring validation.

Usage (from backend/, with venv active and MongoDB running):
    python -m scripts.import_questions
"""
import asyncio
import csv
import re
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

# Allow running as `python -m scripts.import_questions` or `python scripts/import_questions.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import MONGO_URI, MONGO_DB_NAME  # noqa: E402

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "Master_Question_Bank_with_topics_active.csv"

REQUIRED_COLUMNS = {
    "question_id",
    "source_question_number",
    "question",
    "topic",
    "reference_answer",
    "rubric",
    "difficulty",
    "irt_difficulty",
    "active",
}

# Matches numbered list items like "1. ...", "2) ...", "10. ..." at the
# start of a rubric point, so we can split the raw rubric string into parts.
_RUBRIC_ITEM_RE = re.compile(r"(?:^|\s)\d+[.)]\s+")


def parse_rubric(raw: str) -> list[str]:
    """Parse a numbered rubric string (e.g. '1. Point one. 2. Point two.')
    into a clean list of individual rubric point strings.

    Falls back to treating the whole string as one point if no numbering
    is detected, and returns [] for empty/missing rubric text.
    """
    if not raw or not raw.strip():
        return []

    parts = _RUBRIC_ITEM_RE.split(raw.strip())
    points = [p.strip().rstrip(".").strip() for p in parts if p and p.strip()]

    if not points:
        return [raw.strip()]
    return points


def parse_bool(raw: str) -> bool:
    """Parse the CSV's `active` column into a real bool."""
    return str(raw).strip().lower() in {"true", "1", "yes"}


def parse_float(raw: str, field: str, question_id: str) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ValueError(
            f"Row {question_id!r}: could not parse {field!r} value {raw!r} as float"
        )


def load_rows(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Master Question Bank CSV not found at {csv_path}. "
            "Place Master_Question_Bank_with_topics_active.csv in backend/data/ first."
        )

    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing required columns: {sorted(missing)}")
        return list(reader)


def build_documents(rows: list[dict]) -> tuple[list[dict], int]:
    """Return (documents_to_upsert, skipped_inactive_count)."""
    documents = []
    skipped = 0

    for row in rows:
        if not parse_bool(row["active"]):
            skipped += 1
            continue

        question_id = row["question_id"].strip()
        documents.append(
            {
                "question_id": question_id,
                "source_question_number": row["source_question_number"].strip(),
                "question": row["question"].strip(),
                "topic": row["topic"].strip(),
                "reference_answer": row["reference_answer"].strip(),
                "rubric": parse_rubric(row["rubric"]),
                "difficulty": row["difficulty"].strip(),
                "irt_difficulty": parse_float(row["irt_difficulty"], "irt_difficulty", question_id),
                "active": True,
            }
        )

    return documents, skipped


async def import_questions() -> None:
    rows = load_rows(CSV_PATH)
    documents, skipped = build_documents(rows)

    if not documents:
        print(f"No active rows found in {CSV_PATH} — nothing to import.")
        return

    client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]
    collection = db["questions"]

    await collection.create_index("question_id", unique=True)

    upserted = 0
    modified = 0
    for doc in documents:
        result = await collection.update_one(
            {"question_id": doc["question_id"]},
            {"$set": doc},
            upsert=True,
        )
        if result.upserted_id is not None:
            upserted += 1
        elif result.modified_count:
            modified += 1

    total_in_collection = await collection.count_documents({})
    client.close()

    print(f"Read {len(rows)} rows from {CSV_PATH.name}")
    print(f"Skipped {skipped} inactive row(s)")
    print(f"Upserted {upserted} new question(s), updated {modified} existing question(s)")
    print(f"questions collection now has {total_in_collection} document(s) total")


if __name__ == "__main__":
    asyncio.run(import_questions())
