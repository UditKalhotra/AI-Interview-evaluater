"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Navbar from "../components/Navbar";
import QuestionCard from "../components/QuestionCard";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function TechnicalInterviewContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [sessionId, setSessionId] = useState(null);
  const [candidateName, setCandidateName] = useState("");
  const [currentQuestionId, setCurrentQuestionId] = useState(null);
  const [currentQuestionData, setCurrentQuestionData] = useState(null);
  const [sessionStatus, setSessionStatus] = useState("initializing");
  const [loadError, setLoadError] = useState(null);

  const [theta, setTheta] = useState(0.0);
  const [standardError, setStandardError] = useState(1.0);
  const [answeredCount, setAnsweredCount] = useState(0);

  // Initialize or resume session
  useEffect(() => {
    async function initSession() {
      const existingSid = searchParams.get("session_id");
      const cName = searchParams.get("candidate");
      if (cName) setCandidateName(cName);

      if (existingSid) {
        setSessionId(existingSid);
        try {
          const res = await fetch(
            `${API_URL}/interview/session/${encodeURIComponent(existingSid)}/next-question`
          );
          if (res.ok) {
            const data = await res.json();
            setTheta(data.theta ?? 0.0);
            setStandardError(data.standard_error ?? 1.0);
            setAnsweredCount(data.answered_count ?? 0);

            if (data.is_complete) {
              setSessionStatus("complete");
              router.push(`/report?session_id=${encodeURIComponent(existingSid)}`);
              return;
            }

            setCurrentQuestionId(data.next_question_id || "MOHLER_1_1");
            setCurrentQuestionData(data.next_question || null);
            setSessionStatus("in_progress");
            return;
          }
        } catch (e) {
          console.warn("Could not resume session, initializing new session", e);
        }
      }

      // Start new session
      try {
        setSessionStatus("initializing");
        const res = await fetch(`${API_URL}/interview/session/start`, {
          method: "POST",
        });
        if (!res.ok) throw new Error(`Failed to initialize session (${res.status})`);
        const data = await res.json();
        setSessionId(data.session_id);
        setCurrentQuestionId(data.current_question_id || "MOHLER_1_1");
        setCurrentQuestionData(data.initial_question || null);
        setTheta(data.theta ?? 0.0);
        setStandardError(data.standard_error ?? 1.0);
        setSessionStatus("in_progress");
      } catch (err) {
        setLoadError(err.message);
        setSessionStatus("error");
      }
    }

    initSession();
  }, [searchParams, router]);

  const handleTurnCompleted = (advanceData) => {
    setTheta(advanceData.theta ?? 0.0);
    setStandardError(advanceData.standard_error ?? 1.0);
    setAnsweredCount(advanceData.answered_count ?? 0);

    if (advanceData.is_complete) {
      setSessionStatus("complete");
      setTimeout(() => {
        router.push(`/report?session_id=${encodeURIComponent(sessionId)}`);
      }, 1200);
    } else if (advanceData.next_question_id) {
      setCurrentQuestionId(advanceData.next_question_id);
      setCurrentQuestionData(advanceData.next_question || null);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#0b0f19" }}>
      <Navbar />

      <main style={{ flex: 1, padding: "2rem 1.5rem", maxWidth: "900px", margin: "0 auto", width: "100%" }}>
        {/* Error Banner */}
        {loadError && (
          <div
            style={{
              padding: "1rem 1.25rem",
              background: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "#fca5a5",
              borderRadius: "12px",
              marginBottom: "1.5rem",
              textAlign: "center",
            }}
          >
            ⚠️ Session Error: {loadError}
          </div>
        )}

        {/* Loading State */}
        {sessionStatus === "initializing" && (
          <div style={{ textAlign: "center", padding: "5rem 2rem", color: "#94a3b8" }}>
            <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⏳</div>
            <h3 style={{ color: "#f8fafc", marginBottom: "0.5rem" }}>Initializing Assessment Room...</h3>
            <p style={{ fontSize: "0.9rem", color: "#64748b" }}>Calibrating IRT adaptive engine & loading baseline question.</p>
          </div>
        )}

        {/* Live In-Progress Session */}
        {sessionStatus === "in_progress" && sessionId && currentQuestionId && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {/* Top Assessment HUD */}
            <div style={styles.hudBar}>
              <div style={styles.hudItem}>
                <span style={styles.hudLabel}>Candidate</span>
                <span style={styles.hudValue}>{candidateName || "Standard Assessment"}</span>
              </div>

              <div style={styles.hudItem}>
                <span style={styles.hudLabel}>Session ID</span>
                <span style={{ ...styles.hudValue, fontFamily: "monospace", color: "#94a3b8" }}>
                  {sessionId}
                </span>
              </div>

              <div style={styles.hudItem}>
                <span style={styles.hudLabel}>Progress</span>
                <span style={styles.hudValue}>{answeredCount} / 5 Questions</span>
              </div>

              <div style={styles.hudItem}>
                <span style={styles.hudLabel}>IRT Ability Level (\(\theta\))</span>
                <span style={{ ...styles.hudValue, color: "#3b82f6" }}>
                  {theta >= 0 ? `+${theta.toFixed(2)}` : theta.toFixed(2)}
                </span>
              </div>
            </div>

            {/* Question Component */}
            <QuestionCard
              questionId={currentQuestionId}
              sessionId={sessionId}
              questionData={currentQuestionData}
              answeredCount={answeredCount}
              totalQuestions={5}
              onAnswerSubmitted={handleTurnCompleted}
            />
          </div>
        )}

        {/* Complete State */}
        {sessionStatus === "complete" && (
          <div
            style={{
              textAlign: "center",
              padding: "4rem 2rem",
              background: "#151d2a",
              borderRadius: "16px",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              boxShadow: "0 10px 30px rgba(16, 185, 129, 0.1)",
            }}
          >
            <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🎉</div>
            <h2 style={{ color: "#10b981", fontSize: "1.75rem", marginBottom: "0.5rem" }}>
              Assessment Completed!
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "1.05rem", marginBottom: "1.5rem" }}>
              Compiling comprehensive IRT ability, LSA correctness, and speech metrics...
            </p>
            <div style={{ color: "#3b82f6", fontWeight: "600", fontSize: "0.95rem" }}>
              Redirecting to Evaluation Dashboard &rarr;
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

const styles = {
  hudBar: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "1rem",
    padding: "1rem 1.25rem",
    background: "#151d2a",
    borderRadius: "12px",
    border: "1px solid #233044",
  },
  hudItem: {
    display: "flex",
    flexDirection: "column",
    gap: "0.2rem",
  },
  hudLabel: {
    fontSize: "0.725rem",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    color: "#64748b",
  },
  hudValue: {
    fontSize: "0.95rem",
    fontWeight: "600",
    color: "#f8fafc",
  },
};

export default function InterviewPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: "center", padding: "4rem", color: "#94a3b8" }}>Loading assessment room...</div>}>
      <TechnicalInterviewContent />
    </Suspense>
  );
}
