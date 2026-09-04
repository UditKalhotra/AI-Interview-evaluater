"""
Module 3 — Avatar Voice Output (Text-to-Speech).

Given a question_id, fetches that question's `question` text from Module 2's
`questions` collection, synthesizes it to speech via services/tts.py, and
streams the audio back as audio/mpeg for the frontend avatar to play.

This is the first route under the /interview prefix — later modules
(4, 8, 9...) add more routes here, they don't create a parallel router.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.db import get_database
from app.services.tts import synthesize_speech, TTSError

router = APIRouter(prefix="/interview", tags=["interview"])


@router.get("/question-audio/{question_id}")
async def get_question_audio(question_id: str):
    """Return spoken audio (mp3) of the given question's text."""
    db = get_database()
    doc = await db["questions"].find_one({"question_id": question_id})
    if doc is None:
        raise HTTPException(
            status_code=404, detail=f"Question {question_id!r} not found"
        )

    question_text = doc.get("question")
    if not question_text:
        raise HTTPException(
            status_code=422,
            detail=f"Question {question_id!r} has no question text to speak",
        )

    try:
        audio_path = await synthesize_speech(question_text, question_id)
    except TTSError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=f"{question_id}.mp3",
    )
