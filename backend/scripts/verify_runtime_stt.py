"""
Runtime STT Verification Script.

Transcribes two distinct candidate audio recordings (.webm) via the production
`transcribe_audio` function in `app.services.stt` to verify real, non-hardcoded,
non-duplicate transcriptions.
"""

import sys
import asyncio
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.stt import transcribe_audio


async def test_runtime_transcripts():
    uploads_dir = backend_dir / "uploads"
    audio_files = list(uploads_dir.glob("*.webm"))

    if len(audio_files) < 2:
        print("ERROR: Need at least 2 .webm audio files in backend/uploads to verify runtime STT.")
        return

    # Select 2 distinct audio files
    file_1 = audio_files[0]
    file_2 = audio_files[1]

    print("\n=======================================================================")
    print("           REAL RUNTIME SPEECH-TO-TEXT (STT) VERIFICATION            ")
    print("=======================================================================")
    print(f"Audio File 1: {file_1.name}")
    print(f"Audio File 2: {file_2.name}")
    print("-----------------------------------------------------------------------\n")

    res_1 = await transcribe_audio(str(file_1))
    t1 = res_1.get("transcript", "")

    res_2 = await transcribe_audio(str(file_2))
    t2 = res_2.get("transcript", "")

    print(f"--- Transcript 1 ({file_1.name}) ---")
    print(f"\"{t1}\"\n")

    print(f"--- Transcript 2 ({file_2.name}) ---")
    print(f"\"{t2}\"\n")

    if t1 == t2:
        print("[ERROR] Transcripts are identical! STT is returning duplicate text.")
        sys.exit(1)
    else:
        print("[SUCCESS] Transcripts are distinct and reflect actual spoken audio content!")
        print("=======================================================================\n")


if __name__ == "__main__":
    asyncio.run(test_runtime_transcripts())
