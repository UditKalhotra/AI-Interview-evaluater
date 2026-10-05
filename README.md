# 🎙️ AI Voice Interview & Evaluation System

An end-to-end, AI-powered platform for conducting automated voice-based technical and behavioral interviews. The system features an interactive AI avatar with lip-sync animation, real-time Speech-to-Text (STT), Text-to-Speech (TTS), multi-dimensional NLP scoring (TF-IDF, Latent Semantic Analysis), Google Gemini LLM evaluations, speech dynamics analysis, and comprehensive performance feedback reports.

---

## 🚀 Features

### 🎙️ Interactive AI Interviewer
- **Lip-Synced Animated Avatar**: Interactive 2D visual AI interviewer avatar with mouth morphing and canvas animations synchronized with speech playback.
- **Natural Voice Synthesis**: Text-to-Speech (TTS) using OpenAI's high-quality TTS API with zero-config `gTTS` fallback for offline/local dev.

### 🎧 Voice Recording & Live Speech Recognition
- **Real-Time Web Audio Capture**: Browser-based microphone recording with real-time audio visualization waveforms.
- **Multi-Stage STT Fallback Architecture**:
  1. **Primary**: OpenAI Whisper / Google SpeechRecognition API.
  2. **Fallback**: Web Speech API live stream transcription.
  3. **Graceful Error Handling**: Handles silent audio, background noise, or low speech energy seamlessly without breaking session flow.

### 🧠 Multi-Dimensional AI Scoring Engine
- **Technical Accuracy Scoring**:
  - **Keyword & Concept Matching**: Extract key terms and compute coverage against reference answers.
  - **Semantic Vector Similarity**: TF-IDF Cosine Similarity combined with trained **Latent Semantic Analysis (LSA)** models.
  - **Google Gemini LLM Evaluation**: In-depth conceptual correctness, depth of explanation, and technical reasoning analysis.
- **Communication & Speech Dynamics Analysis**:
  - **Speech Tempo (WPM)**: Calculates Words Per Minute to evaluate delivery speed.
  - **Filler Word Detection**: Identifies hesitation markers and filler phrases (*"um"*, *"uh"*, *"like"*, *"you know"*).
  - **Fluency & Energy Metrics**: Assesses pause ratio, speech energy consistency, and clarity.
- **Hybrid Score Aggregation**: Combines NLP metrics, LLM qualitative insights, and audio feature analysis into balanced candidate ratings.

### 📊 Comprehensive Candidate Reports
- **Overall Performance Breakdown**: Overall score, Technical proficiency, Communication clarity, and Fluency index.
- **Question-by-Question Deep Dive**:
  - Candidate spoken transcript vs. Ideal reference answer.
  - Key concepts covered vs. missed.
  - Specific Gemini AI feedback per question.
- **Actionable Growth Insights**: Strategic key strengths and targeted areas for improvement.
- **Print & Export**: Clean candidate evaluation report interface.

---

## 🛠️ Technology Stack

- **Frontend**: Next.js 16 (App Router), React 19, Vanilla CSS3 (Glassmorphism, CSS Animations, Custom Canvas rendering), HTML5 MediaRecorder API, Web Speech API.
- **Backend**: Python 3.10+, FastAPI, Motor (Async MongoDB Driver), Pydantic v2, Scikit-learn, NumPy, SciPy, Google Gemini API (`google-genai`), OpenAI API, `gTTS`, `SpeechRecognition`, `openai-whisper`.
- **Database**: MongoDB (Local MongoDB Community Server or MongoDB Atlas).

---

## 📁 Repository Structure

```
AI-Interview-evaluater/
├── run_dev.bat                      # One-click Windows startup script for Backend + Frontend
├── README.md                        # Project documentation
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entry point & CORS configuration
│   │   ├── db.py                    # Motor async MongoDB connection & pool management
│   │   ├── models/                  # Pydantic schemas for collections (Questions, Sessions, Answers, Scores)
│   │   ├── routers/
│   │   │   ├── questions.py         # Question bank & topic management routes
│   │   │   └── interview.py         # Session start, audio upload, answer submission, report generation
│   │   ├── services/
│   │   │   ├── stt.py               # Speech-to-Text service with Whisper & Google fallbacks
│   │   │   ├── tts.py               # Text-to-Speech service (OpenAI TTS & gTTS fallback)
│   │   │   ├── scoring.py           # NLP scoring engine (TF-IDF, LSA, communication metrics)
│   │   │   ├── gemini.py            # Gemini API integration for LLM answer scoring & report feedback
│   │   │   ├── features.py          # Audio feature extraction (tempo, pauses, filler words)
│   │   │   └── report.py            # Session report generation & metrics aggregation
│   │   └── schemas/                 # API request & response payload schemas
│   ├── data/
│   │   ├── Data.csv                 # Core interview dataset
│   │   ├── Master_Question_Bank... # Topic-categorized question dataset
│   │   └── lsa_pipeline.joblib      # Pre-trained Latent Semantic Analysis model
│   ├── scripts/                     # Data seeding & validation scripts
│   │   ├── import_questions.py      # Seed MongoDB with questions from CSV
│   │   ├── train_lsa.py             # Train LSA model on reference answer corpus
│   │   ├── validate_scoring.py      # Verify scoring engine calculations
│   │   └── test_e2e_session.py      # End-to-end integration test runner
│   ├── uploads/                     # Local storage for recorded audio files (.wav / .webm)
│   ├── requirements.txt             # Python dependencies
│   ├── .env.example                 # Backend environment variable template
│   └── run_backend.bat              # Standalone script to start uvicorn backend
└── frontend/
    ├── app/
    │   ├── page.js                  # Home page: Interview configuration & session setup
    │   ├── interview/page.js        # Live Interview page: Avatar, voice recorder, audio playback
    │   ├── report/page.js           # Candidate Evaluation Report page: Analytics & score breakdowns
    │   ├── components/
    │   │   ├── Avatar.js            # Animated AI Avatar component with lip-sync logic
    │   │   ├── QuestionCard.js      # Interactive question display component
    │   │   └── Navbar.js            # Top navigation header
    │   ├── globals.css              # Global styles & design system tokens
    │   └── layout.js                # Root layout component
    ├── package.json                 # Next.js & React dependencies
    └── .env.local.example           # Frontend environment variable template
```

---

## ⚡ Getting Started

### Prerequisites

- **Python**: `3.10+` installed
- **Node.js**: `18.0+` installed
- **MongoDB**: Community Edition running on `localhost:27017` (or MongoDB Atlas connection URI)
- **FFmpeg** *(Optional, recommended for Whisper local audio processing)*: Required by `openai-whisper` for non-WAV audio conversion.

---

### 1. Database Setup

Ensure MongoDB service is running locally on port `27017`:
```bash
mongod --dbpath /path/to/data/db
```

---

### 2. Quick Start (Windows Launcher)

Simply double-click or run `run_dev.bat` from the root directory:
```cmd
run_dev.bat
```
This automatically launches both the FastAPI backend on port `8000` and the Next.js frontend on port `3000`.

---

### 3. Manual Step-by-Step Setup

#### A. Backend Setup

1. Open a terminal and navigate to `backend/`:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows (cmd/PowerShell):
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and configure your API keys (see [Environment Variables](#-environment-variables) section).

5. Seed questions into MongoDB database:
   ```bash
   python scripts/import_questions.py
   ```

6. Train the LSA (Latent Semantic Analysis) scoring model:
   ```bash
   python scripts/train_lsa.py
   ```

7. Start the backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Verify backend health at `http://localhost:8000/health`.

---

#### B. Frontend Setup

1. Open a second terminal and navigate to `frontend/`:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables (optional):
   ```bash
   cp .env.local.example .env.local
   ```
   *(Default points to `http://localhost:8000`)*

4. Start the Next.js development server:
   ```bash
   npm run dev
   ```

5. Open your browser and navigate to `http://localhost:3000`.

---

## ⚙️ Environment Variables

### Backend `.env`

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGO_DB_NAME` | Database name | `voice_interview_db` |
| `GEMINI_API_KEY` | Google Gemini API Key (for LLM evaluations) | `AIzaSy...` *(Optional, falls back to rule-based scoring)* |
| `TTS_API_KEY` | OpenAI API Key for high quality TTS | `sk-...` *(Optional, falls back to `gTTS`)* |
| `TTS_MODEL` | OpenAI TTS model version | `tts-1` |
| `TTS_VOICE` | OpenAI TTS voice style | `alloy` |

### Frontend `.env.local`

| Variable | Description | Default |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Backend FastAPI server base URL | `http://localhost:8000` |

---

## 🔌 Core API Endpoints

### 🩺 System & Questions
- `GET /health` — Check backend status and MongoDB connectivity.
- `GET /api/questions/topics` — List available question topics and categories.
- `GET /api/questions` — Fetch questions filtered by role, category, or difficulty.

### 🎙️ Interview Workflow
- `POST /api/interview/start` — Initialize a new interview session.
- `POST /api/interview/submit-answer` — Upload audio recording / answer text for processing and real-time evaluation.
- `POST /api/interview/finish` — Finalize interview session and trigger aggregate evaluation.
- `GET /api/interview/session/{session_id}/report` — Retrieve candidate report analytics and scores.

---

## 🛠️ Data & Model Management Scripts

The `backend/scripts/` directory includes setup and training scripts:

```bash
# Seed questions into MongoDB database from CSV files
python scripts/import_questions.py

# Train Latent Semantic Analysis (LSA) model on reference answer corpus
python scripts/train_lsa.py
```


