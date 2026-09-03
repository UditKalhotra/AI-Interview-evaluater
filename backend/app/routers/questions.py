"""
Module 2 — /questions router.

Read-only inspection endpoints over the `questions` collection populated by
scripts/import_questions.py. No write endpoints here — the CSV import script
is the only writer for this module.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.db import get_database

router = APIRouter(prefix="/questions", tags=["questions"])


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("")
async def list_questions(topic: Optional[str] = Query(default=None)):
    """List all questions, optionally filtered by topic (case-insensitive exact match)."""
    db = get_database()
    query: dict = {}
    if topic:
        query["topic"] = {"$regex": f"^{topic}$", "$options": "i"}

    cursor = db["questions"].find(query)
    return [_serialize(doc) async for doc in cursor]


@router.get("/{question_id}")
async def get_question(question_id: str):
    """Fetch a single question by its question_id."""
    db = get_database()
    doc = await db["questions"].find_one({"question_id": question_id})
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Question {question_id!r} not found")
    return _serialize(doc)
