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
  totalQuestions = 0,
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

    if (prepTimerRef.current) clearInterval(prepTimerRef.current);
    if (answerTimerRef.current) clearInterval(answerTimerRef.current);

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

  const handleRepeatQuestion = () => {
    setRepeatCount((prev) => prev + 1);
    setRepeatNotice(true);
    setTimeout(() => setRepeatNotice(false), 2500);

    if (phase === "prep") {
      setPrepTimeLeft(PREP_TIME_DEFAULT);
    }
  };

  const handleReadyToAnswer = () => {
    if (prepTimerRef.current) clearInterval(prepTimerRef.current);
    setPhase("ready");
  };

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

  const stopRecording = () => {
    if (answerTimerRef.current) clearInterval(answerTimerRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      setPhase("submitting");
    }
  };

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
          <p style={styles.loadingText}>Loading question statement...</p>
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
          {errorMessage}
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

            <div style={styles.progressTrack}>
              <div
                style={{
                  ...styles.progressBar,
                  width: `${(prepTimeLeft / PREP_TIME_DEFAULT) * 100}%`,
                  background: "#315EA8",
                }}
              />
            </div>
            <p style={styles.prepSubtext}>
              Take up to 1 minute to read and formulate your spoken response.
            </p>

            <div style={styles.actionRow}>
              <button style={styles.buttonSecondary} onClick={handleRepeatQuestion}>
                Repeat Question
              </button>
              <button style={styles.buttonPrimary} onClick={handleReadyToAnswer}>
                Ready to Answer
              </button>
            </div>
          </div>
        )}

        {/* Phase 2: Ready to record */}
        {phase === "ready" && (
          <div style={styles.readyContainer}>
            <div style={styles.readyBanner}>
              Preparation time finished. Click below when ready to record your verbal response.
            </div>
            <div style={styles.actionRow}>
              <button style={styles.buttonSecondary} onClick={handleRepeatQuestion}>
                Repeat Question
              </button>
              <button style={styles.buttonRecord} onClick={startRecording}>
                Start Recording
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
                <span>Recording Spoken Response</span>
              </div>
              <span style={styles.recordingTimer}>
                0:{answerTimeLeft < 10 ? `0${answerTimeLeft}` : answerTimeLeft}
              </span>
            </div>

            <div style={styles.progressTrack}>
              <div
                style={{
                  ...styles.progressBar,
                  width: `${(answerTimeLeft / ANSWER_TIME_DEFAULT) * 100}%`,
                  background: "#B55353",
                }}
              />
            </div>

            <div style={styles.actionRow}>
              <button style={styles.buttonSecondary} onClick={handleRepeatQuestion}>
                Repeat Question
              </button>
              <button style={styles.buttonStop} onClick={stopRecording}>
                Submit Response
              </button>
            </div>
          </div>
        )}

        {/* Phase 4: Submitting */}
        {phase === "submitting" && (
          <div style={styles.submittingBox}>
            <div style={{ fontWeight: "600", color: "#111827", fontSize: "0.9375rem" }}>
              Processing Spoken Response...
            </div>
            <div style={{ fontSize: "0.8125rem", color: "#667085" }}>
              Transcribing audio and calculating evaluation metrics.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  card: {
    background: "#FFFFFF",
    borderRadius: "8px",
    border: "1px solid #E2E4E7",
    padding: "1.75rem",
    display: "flex",
    flexDirection: "column",
    gap: "1.25rem",
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
    gap: "0.5rem",
    flexWrap: "wrap",
  },
  questionIndexBadge: {
    background: "#F1F2F0",
    border: "1px solid #E2E4E7",
    color: "#111827",
    fontSize: "0.75rem",
    fontWeight: "700",
    padding: "0.25rem 0.6rem",
    borderRadius: "4px",
  },
  topicBadge: {
    background: "#F1F2F0",
    border: "1px solid #E2E4E7",
    color: "#667085",
    fontSize: "0.75rem",
    fontWeight: "600",
    padding: "0.25rem 0.6rem",
    borderRadius: "4px",
  },
  difficultyBadge: {
    fontSize: "0.75rem",
    fontWeight: "600",
    padding: "0.25rem 0.6rem",
    borderRadius: "4px",
    border: "1px solid",
  },
  diffEasy: {
    background: "#EAF3ED",
    color: "#3F7D5A",
    borderColor: "#C8E2D2",
  },
  diffMedium: {
    background: "#F8F3E9",
    color: "#A87832",
    borderColor: "#E8D7BE",
  },
  diffHard: {
    background: "#F9EBEB",
    color: "#B55353",
    borderColor: "#ECC6C6",
  },
  repeatBadge: {
    fontSize: "0.75rem",
    color: "#667085",
    background: "#F1F2F0",
    border: "1px solid #E2E4E7",
    padding: "0.2rem 0.5rem",
    borderRadius: "4px",
  },
  loadingBox: {
    padding: "2.5rem 1.5rem",
    textAlign: "center",
  },
  loadingText: {
    color: "#667085",
    fontSize: "0.9375rem",
  },
  questionBox: {
    background: "#F7F7F5",
    border: "1px solid #E2E4E7",
    borderRadius: "6px",
    padding: "1.5rem",
  },
  questionBoxHighlight: {
    borderColor: "#315EA8",
  },
  questionLabelRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "0.5rem",
  },
  questionLabel: {
    fontSize: "0.75rem",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    color: "#667085",
  },
  noticeTag: {
    fontSize: "0.75rem",
    color: "#315EA8",
    fontWeight: "600",
  },
  questionText: {
    fontSize: "1.25rem",
    fontWeight: "700",
    color: "#111827",
    lineHeight: "1.4",
  },
  errorBox: {
    padding: "0.75rem 1rem",
    background: "#F9EBEB",
    border: "1px solid #ECC6C6",
    color: "#B55353",
    borderRadius: "6px",
    fontSize: "0.875rem",
  },
  controlsSection: {
    borderTop: "1px solid #E2E4E7",
    paddingTop: "1.25rem",
  },
  prepContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "0.85rem",
  },
  timerHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  timerTitle: {
    color: "#667085",
    fontSize: "0.875rem",
    fontWeight: "600",
  },
  timerValue: {
    color: "#315EA8",
    fontSize: "1.15rem",
    fontWeight: "700",
    fontVariantNumeric: "tabular-nums",
  },
  progressTrack: {
    height: "6px",
    background: "#E2E4E7",
    borderRadius: "3px",
    overflow: "hidden",
  },
  progressBar: {
    height: "100%",
    borderRadius: "3px",
    transition: "width 1s linear",
  },
  prepSubtext: {
    fontSize: "0.8125rem",
    color: "#667085",
  },
  readyContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
  },
  readyBanner: {
    padding: "0.75rem 1rem",
    background: "#EAF3ED",
    border: "1px solid #C8E2D2",
    color: "#3F7D5A",
    borderRadius: "6px",
    fontSize: "0.875rem",
    fontWeight: "600",
  },
  recordingContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
  },
  recordingHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  recordingLiveBadge: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
    color: "#B55353",
    fontWeight: "700",
    fontSize: "0.875rem",
  },
  pulseDot: {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    background: "#B55353",
  },
  recordingTimer: {
    color: "#111827",
    fontWeight: "700",
    fontSize: "1rem",
  },
  actionRow: {
    display: "flex",
    gap: "0.85rem",
    justifyContent: "flex-end",
    flexWrap: "wrap",
    marginTop: "0.25rem",
  },
  buttonPrimary: {
    padding: "0.65rem 1.35rem",
    borderRadius: "6px",
    background: "#315EA8",
    color: "#ffffff",
    border: "none",
    fontWeight: "600",
    fontSize: "0.875rem",
    cursor: "pointer",
  },
  buttonSecondary: {
    padding: "0.65rem 1.15rem",
    borderRadius: "6px",
    background: "#FFFFFF",
    border: "1px solid #E2E4E7",
    color: "#111827",
    fontWeight: "600",
    fontSize: "0.875rem",
    cursor: "pointer",
  },
  buttonRecord: {
    padding: "0.65rem 1.5rem",
    borderRadius: "6px",
    background: "#3F7D5A",
    color: "#ffffff",
    border: "none",
    fontWeight: "700",
    fontSize: "0.875rem",
    cursor: "pointer",
  },
  buttonStop: {
    padding: "0.65rem 1.5rem",
    borderRadius: "6px",
    background: "#B55353",
    color: "#ffffff",
    border: "none",
    fontWeight: "700",
    fontSize: "0.875rem",
    cursor: "pointer",
  },
  submittingBox: {
    display: "flex",
    flexDirection: "column",
    gap: "0.25rem",
    padding: "1rem 1.25rem",
    background: "#F1F2F0",
    borderRadius: "6px",
    border: "1px solid #E2E4E7",
  },
};
