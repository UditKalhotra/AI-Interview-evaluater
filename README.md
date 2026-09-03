# Voice Interview System — Module 1: Project Scaffolding & Shared Data Layer

No Docker, no auth. Backend and frontend run locally with plain commands,
MongoDB runs as a local service. Two terminals: one for backend, one for
frontend.

## What's here

- `backend/` — FastAPI + Motor (async MongoDB driver), `/health` endpoint,
  Pydantic models for the four core collections (`questions`, `sessions`,
  `answers`, `score_results`).
- `frontend/` — minimal Next.js app with one page that calls `/health` and
  shows "Backend connected".

No business logic yet — that starts in Module 2.

## Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB installed and runnable locally (`mongod`), e.g. via
  [MongoDB Community Server](https://www.mongodb.com/try/download/community)
  or your OS package manager. No container needed.

## 1. Start MongoDB

Start `mongod` however you normally would on your machine (as a background
service, or `mongod --dbpath <your-data-dir>` in its own terminal). It should
be listening on `localhost:27017`.

## 2. Backend (Terminal 1)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # defaults already point at localhost:27017
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/health` — you should see:

```json
{"status": "ok", "database": {"connected": true, "name": "voice_interview_db"}}
```

If `mongod` isn't running yet, `connected` will be `false` but the API still
boots — it doesn't crash on a missing DB.

## 3. Frontend (Terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` — it calls the backend's `/health` endpoint and
shows "Backend connected" plus the database connection status.

If your backend isn't on `localhost:8000`, copy `.env.local.example` to
`.env.local` and set `NEXT_PUBLIC_API_URL`.

## Repo layout

```
backend/
  app/
    models/    <- Pydantic models mirroring MongoDB document shapes
    routers/   <- one file per module's API routes (empty until Module 2)
    services/  <- business logic per module (empty until Module 3+)
    schemas/   <- Pydantic request/response schemas (empty until later modules)
    db.py      <- MongoDB connection (Motor async client)
    main.py
  data/        <- Data.csv and Master_Question_Bank CSV go here (Module 2)
  scripts/     <- import_questions.py, validate_scoring.py (later modules)
  requirements.txt
  .env.example
frontend/
  app/
  package.json
```
