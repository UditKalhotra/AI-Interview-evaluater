"use client";

import { useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEFAULT_TIME_LIMIT = 60; // seconds

/**
 * Module 3 & Module 4 — Avatar Voice Output & Voice Capture with Speech-to-Text.
 *
 * 1. Module 3: Plays question audio from GET /interview/question-audio/{question_id}.
 * 2. Module 4: Once question audio finishes:
 *    - Enables Record Answer button.
 *    - Measures response_time_seconds from question completion to recording start.
 *    - Counts down visible timer limit (e.g. 60s).
 *    - Uploads audio blob to POST /interview/submit-answer.
 *    - Displays the transcribed answer.
 */
export default function Avatar({
  questionId,
  sessionId = "demo_session_1",
  timeLimit = DEFAULT_TIME_LIMIT,
  onPlaybackEnd,
  onAnswerSubmitted,
}) {
  const audioRef = useRef(null);
  const objectUrlRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // States: 'idle' | 'loading' | 'speaking' | 'blocked' | 'ready' | 'recording' | 'submitting' | 'submitted' | 'error'
  const [status, setStatus] = useState("idle");
  const [errorMessage, setErrorMessage] = useState(null);

  // Response timing & recording countdown
  const [playbackEndTime, setPlaybackEndTime] = useState(null);
  const [responseTimeSec, setResponseTimeSec] = useState(null);
  const [timeLeft, setTimeLeft] = useState(timeLimit);
  const [transcript, setTranscript] = useState("");
  const [submittedData, setSubmittedData] = useState(null);

  const countdownIntervalRef = useRef(null);

  // Load and auto-play question audio when questionId changes
  useEffect(() => {
    if (!questionId) return;

    let cancelled = false;
    setStatus("loading");
    setErrorMessage(null);
    setTranscript("");
    setSubmittedData(null);
    setPlaybackEndTime(null);
    setResponseTimeSec(null);
    setTimeLeft(timeLimit);

    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
    }

    async function loadAndPlay() {
      try {
        const res = await fetch(
          `${API_URL}/interview/question-audio/${encodeURIComponent(questionId)}`
        );
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Request failed with status ${res.status}`);
        }
        const blob = await res.blob();
        if (cancelled) return;

        if (objectUrlRef.current) {
          URL.revokeObjectURL(objectUrlRef.current);
        }
        const url = URL.createObjectURL(blob);
        objectUrlRef.current = url;

        if (audioRef.current) {
          audioRef.current.src = url;
          try {
            await audioRef.current.play();
            if (!cancelled) setStatus("speaking");
          } catch (playErr) {
            if (!cancelled) setStatus("blocked");
          }
        }
      } catch (err) {
        if (!cancelled) {
          setStatus("error");
          setErrorMessage(err.message || "Could not load question audio");
        }
      }
    }

    loadAndPlay();

    return () => {
      cancelled = true;
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
      }
    };
  }, [questionId, timeLimit]);

  useEffect(() => {
    return () => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    };
  }, []);

  const handleAudioEnded = () => {
    const endTime = Date.now();
    setPlaybackEndTime(endTime);
    setStatus("ready");
    if (onPlaybackEnd) onPlaybackEnd();
  };

  const handleManualPlay = () => {
    if (audioRef.current) {
      audioRef.current
        .play()
        .then(() => setStatus("speaking"))
        .catch(() => setStatus("blocked"));
    }
  };

  // Start recording voice answer
  const startRecording = async () => {
    try {
      setErrorMessage(null);
      // Measure response_time_seconds
      const now = Date.now();
      const startTime = playbackEndTime || now;
      const computedResponseTime = Math.max(0.1, Number(((now - startTime) / 1000).toFixed(2)));
      setResponseTimeSec(computedResponseTime);

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        // Stop all audio tracks from mic
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorderRef.current.mimeType || "audio/webm",
        });
        uploadAnswer(audioBlob, computedResponseTime);
      };

      mediaRecorderRef.current.start();
      setStatus("recording");
      setTimeLeft(timeLimit);

      // Start countdown timer
      countdownIntervalRef.current = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            stopRecording();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err) {
      setStatus("error");
      setErrorMessage(
        err.name === "NotAllowedError"
          ? "Microphone permission denied. Please allow microphone access in your browser."
          : `Recording error: ${err.message}`
      );
    }
  };

  // Stop recording manually or by timer
  const stopRecording = () => {
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
    }
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      mediaRecorderRef.current.stop();
      setStatus("submitting");
    }
  };

  // Upload recorded audio blob to Module 9 advance orchestration endpoint
  const uploadAnswer = async (audioBlob, responseTime) => {
    setStatus("submitting");
    try {
      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("question_id", questionId);
      formData.append("response_time_seconds", responseTime.toString());
      formData.append("file", audioBlob, "answer.webm");

      const res = await fetch(`${API_URL}/interview/session/${encodeURIComponent(sessionId)}/advance`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Advance failed with status ${res.status}`);
      }

      const data = await res.json();
      setSubmittedData(data.last_answer || data);
      setTranscript(data.last_answer?.transcript || "");

      if (data.is_complete) {
        setStatus("complete");
      } else {
        setStatus("submitted");
      }

      if (onAnswerSubmitted) {
        onAnswerSubmitted(data);
      }
    } catch (err) {
      setStatus("error");
      setErrorMessage(err.message || "Failed to submit answer recording");
    }
  };

  return (
    <div style={styles.wrapper}>
      {/* Avatar Visual Indicator */}
      <div
        style={{
          ...styles.avatarCircle,
          ...(status === "speaking" ? styles.avatarSpeaking : {}),
          ...(status === "recording" ? styles.avatarRecording : {}),
        }}
      >
        <span style={styles.speakerIcon}>
          {status === "speaking" && "🔊"}
          {status === "recording" && "🎙️"}
          {status === "submitting" && "⏳"}
          {status === "submitted" && "✅"}
          {(status === "idle" || status === "loading" || status === "ready" || status === "blocked") && "🤖"}
        </span>
      </div>

      <audio
        ref={audioRef}
        onEnded={handleAudioEnded}
        onError={() => setStatus("error")}
      />

      {/* Status Messages */}
      <div style={styles.statusContainer}>
        {status === "loading" && <p style={styles.statusText}>Loading question audio...</p>}
        {status === "speaking" && <p style={styles.statusText}>Avatar is speaking question...</p>}
        {status === "blocked" && (
          <div>
            <p style={styles.statusText}>Audio autoplay was blocked by browser.</p>
            <button style={styles.buttonPlay} onClick={handleManualPlay}>
              ▶ Listen to Question
            </button>
          </div>
        )}
        {status === "ready" && (
          <p style={{ ...styles.statusText, color: "#2563eb", fontWeight: "600" }}>
            Question finished. Click Record when ready!
          </p>
        )}
        {status === "recording" && (
          <div style={styles.recordingBox}>
            <div style={styles.recordingBadge}>🔴 Recording in progress...</div>
            <div style={styles.timerDisplay}>⏱️ {timeLeft}s remaining</div>
            {/* Progress bar */}
            <div style={styles.progressTrack}>
              <div
                style={{
                  ...styles.progressBar,
                  width: `${(timeLeft / timeLimit) * 100}%`,
                }}
              />
            </div>
          </div>
        )}
        {status === "submitting" && (
          <p style={styles.statusText}>Uploading audio & transcribing with STT...</p>
        )}
        {status === "submitted" && (
          <p style={{ ...styles.statusText, color: "#16a34a", fontWeight: "600" }}>
            Answer submitted and transcribed!
          </p>
        )}
        {status === "error" && (
          <p style={styles.errorText}>⚠️ Error: {errorMessage}</p>
        )}
      </div>

      {/* Action Controls */}
      <div style={styles.controlBox}>
        {status === "ready" && (
          <button style={styles.buttonRecord} onClick={startRecording}>
            🎙️ Start Recording
          </button>
        )}
        {status === "recording" && (
          <button style={styles.buttonStop} onClick={stopRecording}>
            ⏹️ Stop & Submit
          </button>
        )}
      </div>

      {/* Submitted Transcript Display */}
      {status === "submitted" && submittedData && (
        <div style={styles.transcriptCard}>
          <h4 style={styles.cardTitle}>Transcribed Answer (Module 4 Output)</h4>
          <div style={styles.metaRow}>
            <span><strong>Response Latency:</strong> {submittedData.response_time_seconds}s</span>
            <span><strong>Audio file:</strong> <code>{submittedData.audio_url}</code></span>
          </div>
          <div style={styles.transcriptBox}>
            <p style={styles.transcriptText}>
              "{submittedData.transcript || "(No speech detected)"}"
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  wrapper: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "1.25rem",
    padding: "2rem",
    maxWidth: "560px",
    margin: "0 auto",
    background: "#ffffff",
    borderRadius: "16px",
    boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05)",
    border: "1px solid #f0f0f0",
  },
  avatarCircle: {
    width: "140px",
    height: "140px",
    borderRadius: "50%",
    background: "#f3f4f6",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "3.2rem",
    transition: "all 0.3s ease",
  },
  avatarSpeaking: {
    boxShadow: "0 0 0 8px rgba(59, 130, 246, 0.3), 0 0 20px rgba(59, 130, 246, 0.2)",
    background: "#eff6ff",
  },
  avatarRecording: {
    boxShadow: "0 0 0 8px rgba(239, 68, 68, 0.3), 0 0 20px rgba(239, 68, 68, 0.2)",
    background: "#fef2f2",
  },
  speakerIcon: {
    lineHeight: 1,
  },
  statusContainer: {
    textAlign: "center",
    minHeight: "48px",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
  },
  statusText: {
    fontFamily: "system-ui, -apple-system, sans-serif",
    color: "#374151",
    fontSize: "1rem",
    margin: 0,
  },
  errorText: {
    fontFamily: "system-ui, -apple-system, sans-serif",
    color: "#dc2626",
    fontSize: "0.95rem",
    margin: 0,
  },
  recordingBox: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "0.5rem",
    width: "100%",
  },
  recordingBadge: {
    fontSize: "0.9rem",
    fontWeight: "600",
    color: "#dc2626",
  },
  timerDisplay: {
    fontSize: "1.25rem",
    fontWeight: "700",
    color: "#1f2937",
  },
  progressTrack: {
    width: "220px",
    height: "6px",
    background: "#e5e7eb",
    borderRadius: "3px",
    overflow: "hidden",
  },
  progressBar: {
    height: "100%",
    background: "#ef4444",
    transition: "width 1s linear",
  },
  controlBox: {
    display: "flex",
    gap: "1rem",
  },
  buttonPlay: {
    padding: "0.6rem 1.4rem",
    fontSize: "0.95rem",
    fontWeight: "600",
    borderRadius: "8px",
    background: "#2563eb",
    color: "#ffffff",
    border: "none",
    cursor: "pointer",
  },
  buttonRecord: {
    padding: "0.75rem 1.75rem",
    fontSize: "1rem",
    fontWeight: "600",
    borderRadius: "10px",
    background: "#2563eb",
    color: "#ffffff",
    border: "none",
    cursor: "pointer",
    boxShadow: "0 4px 12px rgba(37, 99, 235, 0.25)",
    transition: "transform 0.1s ease",
  },
  buttonStop: {
    padding: "0.75rem 1.75rem",
    fontSize: "1rem",
    fontWeight: "600",
    borderRadius: "10px",
    background: "#dc2626",
    color: "#ffffff",
    border: "none",
    cursor: "pointer",
    boxShadow: "0 4px 12px rgba(220, 38, 38, 0.25)",
  },
  transcriptCard: {
    width: "100%",
    marginTop: "1rem",
    padding: "1rem 1.25rem",
    background: "#f9fafb",
    borderRadius: "12px",
    border: "1px solid #e5e7eb",
    textAlign: "left",
  },
  cardTitle: {
    margin: "0 0 0.5rem 0",
    fontSize: "0.95rem",
    color: "#111827",
  },
  metaRow: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: "0.825rem",
    color: "#6b7280",
    marginBottom: "0.75rem",
  },
  transcriptBox: {
    padding: "0.75rem",
    background: "#ffffff",
    borderRadius: "8px",
    border: "1px solid #e5e7eb",
  },
  transcriptText: {
    margin: 0,
    fontSize: "0.95rem",
    color: "#1f2937",
    fontStyle: "italic",
    lineHeight: "1.5",
  },
};
