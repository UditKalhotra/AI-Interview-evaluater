@echo off
echo Launching AI Interview Evaluator Backend and Frontend...
start "Backend (FastAPI)" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
start "Frontend (Next.js)" cmd /k "cd /d %~dp0frontend && npm run dev"
