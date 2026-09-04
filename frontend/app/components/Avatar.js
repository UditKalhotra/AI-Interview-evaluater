"use client";

import { useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Module 3 — Avatar voice output.
 *
 * Given a question_id, fetches spoken audio from
 * GET /interview/question-audio/{question_id} and auto-plays it through a
 * simple static avatar (image + speaker icon). No question text is ever
 * rendered here — audio only, per the voice-only design.
 *
 * Props:
 *   - questionId (string): the question to speak. Component re-fetches and
 *     re-plays whenever this changes.
 *   - onPlaybackEnd (function, optional): called when audio finishes playing.
 *     Module 4 will use this as the signal to enable the record button.
 */
export default function Avatar({ questionId, onPlaybackEnd }) {
  const audioRef = useRef(null);
  const objectUrlRef = useRef(null);
  const [status, setStatus] = useState("idle"); // idle | loading | speaking | error | blocked
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => {
    if (!questionId) return;

    let cancelled = false;
    setStatus("loading");
    setErrorMessage(null);

    async function loadAndPlay() {
      try {
        const res = await fetch(
          `${API_URL}/interview/question-audio/${encodeURIComponent(questionId)}`
        );
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Request failed with ${res.status}`);
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
            // Autoplay can be blocked by the browser until the user
            // interacts with the page. Surface a manual "play" affordance.
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
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questionId]);

  useEffect(() => {
    return () => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    };
  }, []);

  const handleManualPlay = () => {
    if (audioRef.current) {
      audioRef.current
        .play()
        .then(() => setStatus("speaking"))
        .catch(() => setStatus("blocked"));
    }
  };

  return (
    <div style={styles.wrapper}>
      <div style={{ ...styles.avatarCircle, ...(status === "speaking" ? styles.avatarSpeaking : {}) }}>
        <span style={styles.speakerIcon}>{status === "speaking" ? "🔊" : "🎙️"}</span>
      </div>

      <audio
        ref={audioRef}
        onEnded={() => {
          setStatus("idle");
          onPlaybackEnd && onPlaybackEnd();
        }}
        onError={() => setStatus("error")}
      />

      <p style={styles.statusText}>
        {status === "idle" && "Waiting for next question..."}
        {status === "loading" && "Loading question audio..."}
        {status === "speaking" && "Speaking..."}
        {status === "blocked" && "Audio ready — click play to hear the question."}
        {status === "error" && `Audio error: ${errorMessage}`}
      </p>

      {status === "blocked" && (
        <button style={styles.playButton} onClick={handleManualPlay}>
          ▶ Play question
        </button>
      )}
    </div>
  );
}

const styles = {
  wrapper: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "1rem",
    padding: "2rem",
  },
  avatarCircle: {
    width: "160px",
    height: "160px",
    borderRadius: "50%",
    background: "#e6e6e6",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "3rem",
    transition: "box-shadow 0.2s ease",
  },
  avatarSpeaking: {
    boxShadow: "0 0 0 8px rgba(60, 130, 246, 0.25)",
  },
  speakerIcon: {
    lineHeight: 1,
  },
  statusText: {
    fontFamily: "sans-serif",
    color: "#555",
    fontSize: "0.95rem",
  },
  playButton: {
    padding: "0.5rem 1.25rem",
    fontSize: "1rem",
    cursor: "pointer",
  },
};
