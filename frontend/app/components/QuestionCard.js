"use client";

import { useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const PREP_TIME_DEFAULT = 60; // 60 seconds prep reading time
const ANSWER_TIME_DEFAULT = 60; // 60 seconds speaking limit

export default function QuestionCard({
  questionId,
  sessionId,
  questionData,
  answeredCount = 0,
  totalQuestions = 5,
  onAnswerSubmitted,
}) {
  const [questionDetails, setQuestionDetails] = useState(questionData || null);
  const [loadingQuestion, setLoadingQuestion] = useState(!questionData);

  // States: 'prep' (reading time) | 'ready' | 'recording' | 'submitting' | 'submitted' | 'error'
  const [phase, setPhase] = useState("prep");
  const [errorMessage, setErrorMessage] = useState(null);

  // Timers
  const [prepTimeLeft, setPrepTimeLeft] = useState(PREP_TIME_DEFAULT);
  const [answerTimeLeft, setAnswerTimeLeft] = useState(ANSWER_TIME_DEFAULT);
  const [repeatCount, setRepeatCount] = useState(0);
  const [repeatNotice, setRepeatNotice] = useState(false);

  // Recording
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const prepTimerRef = useRef(null);
  const answerTimerRef = useRef(null);
  const prepStartTimeRef = useRef(null);

  // Fetch question text if not supplied directly
  useEffect(() => {
    if (questionData && questionData.question_id === questionId) {
      setQuestionDetails(questionData);
      setLoadingQuestion(false);
    } else if (questionId) {
      setLoadingQuestion(true);
      fetch(`${API_URL}/questions/${encodeURIComponent(questionId)}`)
        .then((res) => {
          if (!res.ok) throw new Error(`Could not fetch question (${res.status})`);
          return res.json();
        })
        .then((data) => {
          setQuestionDetails(data);
          setLoadingQuestion(false);
        })
        .catch((err) => {
          setErrorMessage(err.message);
          setLoadingQuestion(false);
        });
    }
  }, [questionId, questionData]);

  // Reset state when questionId changes
  useEffect(() => {
    setPhase("prep");
    setErrorMessage(null);
    setPrepTimeLeft(PREP_TIME_DEFAULT);
    setAnswerTimeLeft(ANSWER_TIME_DEFAULT);
    setRepeatCount(0);
    setRepeatNotice(false);
    prepStartTimeRef.current = Date.now();

    // Clear existing timers
    if (prepTimerRef.current) clearInterval(prepTimerRef.current);
    if (answerTimerRef.current) clearInterval(answerTimerRef.current);

    // Start 60-second Preparation Reading Timer
    prepTimerRef.current = setInterval(() => {
      setPrepTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(prepTimerRef.current);
          setPhase("ready");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (prepTimerRef.current) clearInterval(prepTimerRef.current);
      if (answerTimerRef.current) clearInterval(answerTimerRef.current);
    };
  }, [questionId]);

  // Handle "Repeat Question" button click
  const handleRepeatQuestion = () => {
    setRepeatCount((prev) => prev + 1);
    setRepeatNotice(true);
    setTimeout(() => setRepeatNotice(false), 2500);

    // If currently in prep mode, reset prep timer to give full 60 seconds again
    if (phase === "prep") {
      setPrepTimeLeft(PREP_TIME_DEFAULT);
    }
  };

  // Move from prep -> ready or start recording directly
  const handleReadyToAnswer = () => {
    if (prepTimerRef.current) clearInterval(prepTimerRef.current);
    setPhase("ready");
  };

  // Start recording answer
  const startRecording = async () => {
    try {
      setErrorMessage(null);
      if (prepTimerRef.current) clearInterval(prepTimerRef.current);

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      const startTime = prepStartTimeRef.current || Date.now();
      const responseLatency = Math.max(0.1, Number(((Date.now() - startTime) / 1000).toFixed(2)));

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorderRef.current.mimeType || "audio/webm",
        });
        uploadAnswer(audioBlob, responseLatency);
      };

      mediaRecorderRef.current.start();
      setPhase("recording");
      setAnswerTimeLeft(ANSWER_TIME_DEFAULT);

      // Start 60-second Speaking Answer Timer
      answerTimerRef.current = setInterval(() => {
        setAnswerTimeLeft((prev) => {
          if (prev <= 1) {
            stopRecording();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err) {
      setPhase("error");
      setErrorMessage(
        err.name === "NotAllowedError"
          ? "Microphone access denied. Please allow microphone permission in your browser."
          : `Microphone error: ${err.message}`
      );
    }
  };

  // Stop recording manually
  const stopRecording = () => {
    if (answerTimerRef.current) clearInterval(answerTimerRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      setPhase("submitting");
    }
  };

  // Upload recording to backend
  const uploadAnswer = async (audioBlob, responseLatency) => {
    setPhase("submitting");
    try {
      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("question_id", questionId);
      formData.append("response_time_seconds", responseLatency.toString());
      formData.append("asked_repeat", repeatCount.toString());
      formData.append("file", audioBlob, "answer.webm");

      const res = await fetch(`${API_URL}/interview/session/${encodeURIComponent(sessionId)}/advance`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Submission failed with status ${res.status}`);
      }

      const data = await res.json();
      setPhase("submitted");

      if (onAnswerSubmitted) {
        onAnswerSubmitted(data);
      }
    } catch (err) {
      setPhase("error");
      setErrorMessage(err.message || "Failed to submit answer");
    }
  };

  const topic = questionDetails?.topic || "Technical Core";
  const difficulty = questionDetails?.difficulty || "Standard";
  const questionText = questionDetails?.question || "Loading question text...";

  return (
    <div style={styles.card}>
      {/* Top Question Meta Header */}
      <div style={styles.cardHeader}>
        <div style={styles.metaBadges}>
          <span style={styles.questionIndexBadge}>
            Question {answeredCount + 1} of {totalQuestions}
          </span>
          <span style={styles.topicBadge}>{topic}</span>
          <span
            style={{
              ...styles.difficultyBadge,
              ...(difficulty === "Easy"
                ? styles.diffEasy
                : difficulty === "Hard"
                ? styles.diffHard
                : styles.diffMedium),
            }}
          >
            {difficulty}
          </span>
        </div>

        {repeatCount > 0 && (
          <span style={styles.repeatBadge}>
            Repeated: {repeatCount}x
          </span>
        )}
      </div>

      {/* Main Question Display Box */}
      {loadingQuestion ? (
        <div style={styles.loadingBox}>
          <div style={styles.spinner} />
          <p style={styles.loadingText}>Fetching question text...</p>
        </div>
      ) : (
        <div style={{ ...styles.questionBox, ...(repeatNotice ? styles.questionBoxHighlight : {}) }}>
          <div style={styles.questionLabelRow}>
            <span style={styles.questionLabel}>Question Statement</span>
            {repeatNotice && <span style={styles.noticeTag}>Display Refreshed</span>}
          </div>
          <h2 style={styles.questionText}>{questionText}</h2>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div style={styles.errorBox}>
          ⚠️ {errorMessage}
        </div>
      )}

      {/* Timer & Controls Section */}
      <div style={styles.controlsSection}>
        {/* Phase 1: Preparation Timer (1 min reading time) */}
        {phase === "prep" && (
          <div style={styles.prepContainer}>
            <div style={styles.timerHeader}>
              <span style={styles.timerTitle}>Reading & Preparation Time</span>
              <span style={styles.timerValue}>0:{prepTimeLeft < 10 ? `0${prepTimeLeft}` : prepTimeLeft}</span>
            </div>

            {/* Preparation Progress Bar */}
            <div style={styles.progressTrack}>
              <div
                style={{
                  ...styles.progressBar,
                  width: `${(prepTimeLeft / PREP_TIME_DEFAULT) * 100}%`,
                  background: "#2563eb",
                }}
              />
            </div>
            <p style={styles.prepSubtext}>
              Take up to 1 minute to read and structure your spoken answer.
            </p>

            <div style={styles.actionRow}>
              <button style={styles.buttonSecondary} onClick={handleRepeatQuestion}>
                🔄 Repeat Question
              </button>
              <button style={styles.buttonPrimary} onClick={handleReadyToAnswer}>
                I'm Ready to Answer &rarr;
              </button>
            </div>
          </div>
        )}

        {/* Phase 2: Ready to record */}
        {phase === "ready" && (
          <div style={styles.readyContainer}>
            <div style={styles.readyBanner}>
              <span>Preparation complete. Click below to record your response.</span>
            </div>
            <div style={styles.actionRow}>
              <button style={styles.buttonSecondary} onClick={handleRepeatQuestion}>
                🔄 Repeat Question
              </button>
              <button style={styles.buttonRecord} onClick={startRecording}>
                🎙️ Start Answering (Record Voice)
              </button>
            </div>
          </div>
        )}

        {/* Phase 3: Recording Answer */}
        {phase === "recording" && (
          <div style={styles.recordingContainer}>
            <div style={styles.recordingHeader}>
              <div style={styles.recordingLiveBadge}>
                <span style={styles.pulseDot} />
                <span>Recording Spoken Answer</span>
              </div>
              <span style={styles.recordingTimer}>
                0:{answerTimeLeft < 10 ? `0${answerTimeLeft}` : answerTimeLeft} remaining
              </span>
            </div>

            <div style={styles.progressTrack}>
              <div
                style={{
                  ...styles.progressBar,
                  width: `${(answerTimeLeft / ANSWER_TIME_DEFAULT) * 100}%`,
                  background: "#ef4444",
                }}
              />
            </div>

            <div style={styles.actionRow}>
              <button style={styles.buttonSecondary} onClick={handleRepeatQuestion}>
                🔄 Repeat Question
              </button>
              <button style={styles.buttonStop} onClick={stopRecording}>
                ⏹️ Finish & Submit Response
              </button>
            </div>
          </div>
        )}

        {/* Phase 4: Submitting */}
        {phase === "submitting" && (
          <div style={styles.submittingBox}>
            <div style={styles.spinner} />
            <div>
              <div style={{ fontWeight: "600", color: "#f8fafc" }}>Processing Spoken Answer...</div>
              <div style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
                Transcribing audio, evaluating technical accuracy & speech metrics...
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  card: {
    background: "#151d2a",
    borderRadius: "16px",
    border: "1px solid #233044",
    padding: "2rem",
    boxShadow: "0 10px 30px rgba(0, 0, 0, 0.2)",
    display: "flex",
    flexDirection: "column",
    gap: "1.5rem",
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "0.75rem",
  },
  metaBadges: {
    display: "flex",
    alignItems: "center",
    gap: "0.6rem",
    flexWrap: "wrap",
  },
  questionIndexBadge: {
    background: "#233044",
    color: "#f8fafc",
    fontSize: "0.8rem",
    fontWeight: "700",
    padding: "0.3rem 0.75rem",
    borderRadius: "6px",
    letterSpacing: "0.02em",
  },
  topicBadge: {
    background: "rgba(37, 99, 235, 0.12)",
    border: "1px solid rgba(37, 99, 235, 0.3)",
    color: "#60a5fa",
    fontSize: "0.8rem",
    fontWeight: "600",
    padding: "0.3rem 0.75rem",
    borderRadius: "6px",
  },
  difficultyBadge: {
    fontSize: "0.8rem",
    fontWeight: "600",
    padding: "0.3rem 0.75rem",
    borderRadius: "6px",
  },
  diffEasy: {
    background: "rgba(16, 185, 129, 0.12)",
    color: "#10b981",
    border: "1px solid rgba(16, 185, 129, 0.3)",
  },
  diffMedium: {
    background: "rgba(245, 158, 11, 0.12)",
    color: "#f59e0b",
    border: "1px solid rgba(245, 158, 11, 0.3)",
  },
  diffHard: {
    background: "rgba(239, 68, 68, 0.12)",
    color: "#ef4444",
    border: "1px solid rgba(239, 68, 68, 0.3)",
  },
  repeatBadge: {
    fontSize: "0.775rem",
    color: "#94a3b8",
    background: "#0f1724",
    border: "1px solid #233044",
    padding: "0.25rem 0.6rem",
    borderRadius: "6px",
  },
  loadingBox: {
    padding: "3rem 1.5rem",
    textAlign: "center",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "1rem",
  },
  loadingText: {
    color: "#94a3b8",
    fontSize: "0.95rem",
  },
  questionBox: {
    background: "#0f1724",
    border: "1px solid #233044",
    borderRadius: "12px",
    padding: "1.75rem",
    transition: "all 0.3s ease",
  },
  questionBoxHighlight: {
    borderColor: "#3b82f6",
    boxShadow: "0 0 16px rgba(59, 130, 246, 0.15)",
  },
  questionLabelRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "0.75rem",
  },
  questionLabel: {
    fontSize: "0.75rem",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    color: "#64748b",
  },
  noticeTag: {
    fontSize: "0.75rem",
    color: "#3b82f6",
    fontWeight: "600",
  },
  questionText: {
    fontSize: "1.35rem",
    fontWeight: "600",
    color: "#f8fafc",
    lineHeight: "1.5",
    letterSpacing: "-0.01em",
  },
  errorBox: {
    padding: "0.85rem 1.25rem",
    background: "rgba(239, 68, 68, 0.12)",
    border: "1px solid rgba(239, 68, 68, 0.3)",
    color: "#fca5a5",
    borderRadius: "10px",
    fontSize: "0.9rem",
  },
  controlsSection: {
    borderTop: "1px solid #233044",
    paddingTop: "1.5rem",
  },
  prepContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
  },
  timerHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  timerTitle: {
    color: "#94a3b8",
    fontSize: "0.9rem",
    fontWeight: "600",
  },
  timerValue: {
    color: "#3b82f6",
    fontSize: "1.25rem",
    fontWeight: "700",
    fontVariantNumeric: "tabular-nums",
  },
  progressTrack: {
    height: "6px",
    background: "#0f1724",
    borderRadius: "3px",
    overflow: "hidden",
  },
  progressBar: {
    height: "100%",
    borderRadius: "3px",
    transition: "width 1s linear",
  },
  prepSubtext: {
    fontSize: "0.85rem",
    color: "#64748b",
  },
  readyContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "1.25rem",
  },
  readyBanner: {
    padding: "0.85rem 1.25rem",
    background: "rgba(16, 185, 129, 0.1)",
    border: "1px solid rgba(16, 185, 129, 0.25)",
    color: "#10b981",
    borderRadius: "10px",
    fontSize: "0.9rem",
    fontWeight: "600",
  },
  recordingContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "1.25rem",
  },
  recordingHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  recordingLiveBadge: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    color: "#ef4444",
    fontWeight: "700",
    fontSize: "0.95rem",
  },
  pulseDot: {
    width: "10px",
    height: "10px",
    borderRadius: "50%",
    background: "#ef4444",
    boxShadow: "0 0 8px #ef4444",
  },
  recordingTimer: {
    color: "#f8fafc",
    fontWeight: "700",
    fontSize: "1.1rem",
  },
  actionRow: {
    display: "flex",
    gap: "1rem",
    justifyContent: "flex-end",
    flexWrap: "wrap",
    marginTop: "0.5rem",
  },
  buttonPrimary: {
    padding: "0.75rem 1.5rem",
    borderRadius: "10px",
    background: "#2563eb",
    color: "#ffffff",
    border: "none",
    fontWeight: "600",
    fontSize: "0.95rem",
    cursor: "pointer",
    transition: "background 0.2s ease",
  },
  buttonSecondary: {
    padding: "0.75rem 1.25rem",
    borderRadius: "10px",
    background: "#0f1724",
    border: "1px solid #233044",
    color: "#cbd5e1",
    fontWeight: "600",
    fontSize: "0.95rem",
    cursor: "pointer",
    transition: "all 0.2s ease",
  },
  buttonRecord: {
    padding: "0.75rem 1.75rem",
    borderRadius: "10px",
    background: "#10b981",
    color: "#ffffff",
    border: "none",
    fontWeight: "700",
    fontSize: "0.95rem",
    cursor: "pointer",
    boxShadow: "0 4px 14px rgba(16, 185, 129, 0.25)",
  },
  buttonStop: {
    padding: "0.75rem 1.75rem",
    borderRadius: "10px",
    background: "#ef4444",
    color: "#ffffff",
    border: "none",
    fontWeight: "700",
    fontSize: "0.95rem",
    cursor: "pointer",
    boxShadow: "0 4px 14px rgba(239, 68, 68, 0.25)",
  },
  submittingBox: {
    display: "flex",
    alignItems: "center",
    gap: "1rem",
    padding: "1.25rem",
    background: "#0f1724",
    borderRadius: "10px",
    border: "1px solid #233044",
  },
  spinner: {
    width: "24px",
    height: "24px",
    border: "3px solid #233044",
    borderTopColor: "#3b82f6",
    borderRadius: "50%",
    animation: "spin 1s linear infinite",
  },
};
