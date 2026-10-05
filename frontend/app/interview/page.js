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
  const [topic, setTopic] = useState("");
  const [candidateName, setCandidateName] = useState("");
  const [currentQuestionId, setCurrentQuestionId] = useState(null);
  const [currentQuestionData, setCurrentQuestionData] = useState(null);
  const [sessionStatus, setSessionStatus] = useState("initializing");
  const [loadError, setLoadError] = useState(null);

  const [answeredCount, setAnsweredCount] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);

  // Initialize or resume session
  useEffect(() => {
    async function initSession() {
      const existingSid = searchParams.get("session_id");
      const topicParam = searchParams.get("topic");
      const cName = searchParams.get("candidate");
      if (cName) setCandidateName(cName);
      if (topicParam) setTopic(topicParam);

      if (existingSid) {
        setSessionId(existingSid);
        try {
          const res = await fetch(
            `${API_URL}/interview/session/${encodeURIComponent(existingSid)}/next-question`
          );
          if (res.ok) {
            const data = await res.json();
            if (data.topic) setTopic(data.topic);
            setAnsweredCount(data.answered_count ?? 0);
            setTotalQuestions(data.total_questions ?? 0);

            if (data.is_complete) {
              setSessionStatus("complete");
              router.push(`/report?session_id=${encodeURIComponent(existingSid)}`);
              return;
            }

            setCurrentQuestionId(data.next_question_id || null);
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
        const formData = new FormData();
        if (topicParam) formData.append("topic", topicParam);

        const res = await fetch(`${API_URL}/interview/session/start`, {
          method: "POST",
          body: formData,
        });
        if (!res.ok) throw new Error(`Failed to initialize session (${res.status})`);
        const data = await res.json();
        setSessionId(data.session_id);
        if (data.topic) setTopic(data.topic);
        setCurrentQuestionId(data.current_question_id || null);
        setCurrentQuestionData(data.initial_question || null);
        setAnsweredCount(data.answered_count ?? 0);
        setTotalQuestions(data.total_questions ?? 0);
        setSessionStatus("in_progress");
      } catch (err) {
        setLoadError(err.message);
        setSessionStatus("error");
      }
    }

    initSession();
  }, [searchParams, router]);

  const handleTurnCompleted = (advanceData) => {
    setAnsweredCount(advanceData.answered_count ?? 0);
    setTotalQuestions(advanceData.total_questions ?? 0);

    if (advanceData.is_complete) {
      setSessionStatus("complete");
      setTimeout(() => {
        router.push(`/report?session_id=${encodeURIComponent(sessionId)}`);
      }, 1000);
    } else if (advanceData.next_question_id) {
      setCurrentQuestionId(advanceData.next_question_id);
      setCurrentQuestionData(advanceData.next_question || null);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#F7F7F5", color: "#111827" }}>
      <Navbar />

      <main style={{ flex: 1, padding: "2rem 1.5rem", maxWidth: "900px", margin: "0 auto", width: "100%" }}>
        {/* Error Banner */}
        {loadError && (
          <div
            style={{
              padding: "0.85rem 1.25rem",
              background: "#F9EBEB",
              border: "1px solid #ECC6C6",
              color: "#B55353",
              borderRadius: "6px",
              marginBottom: "1.5rem",
              fontSize: "0.875rem",
              textAlign: "center",
            }}
          >
            Session Error: {loadError}
          </div>
        )}

        {/* Loading State */}
        {sessionStatus === "initializing" && (
          <div style={{ textAlign: "center", padding: "5rem 2rem", color: "#667085" }}>
            <h3 style={{ color: "#111827", marginBottom: "0.5rem", fontSize: "1.1rem", fontWeight: "600" }}>Initializing Assessment Session</h3>
            <p style={{ fontSize: "0.875rem" }}>Loading topic questions and environment.</p>
          </div>
        )}

        {/* Live In-Progress Session */}
        {sessionStatus === "in_progress" && sessionId && currentQuestionId && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {/* Top Assessment HUD */}
            <div style={styles.hudBar}>
              <div style={styles.hudItem}>
                <span style={styles.hudLabel}>Candidate</span>
                <span style={styles.hudValue}>{candidateName || "Candidate"}</span>
              </div>

              <div style={styles.hudItem}>
                <span style={styles.hudLabel}>Topic</span>
                <span style={{ ...styles.hudValue, color: "#315EA8" }}>{topic || "General"}</span>
              </div>

              <div style={styles.hudItem}>
                <span style={styles.hudLabel}>Progress</span>
                <span style={styles.hudValue}>
                  Question {answeredCount + 1} of {totalQuestions}
                </span>
              </div>

              <div style={styles.hudItem}>
                <span style={styles.hudLabel}>Session ID</span>
                <span style={{ ...styles.hudValue, fontFamily: "monospace", color: "#667085", fontSize: "0.8125rem" }}>
                  {sessionId}
                </span>
              </div>
            </div>

            {/* Question Component */}
            <QuestionCard
              questionId={currentQuestionId}
              sessionId={sessionId}
              questionData={currentQuestionData}
              answeredCount={answeredCount}
              totalQuestions={totalQuestions}
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
              background: "#FFFFFF",
              borderRadius: "8px",
              border: "1px solid #E2E4E7",
            }}
          >
            <h2 style={{ color: "#3F7D5A", fontSize: "1.5rem", marginBottom: "0.5rem", fontWeight: "700" }}>
              Assessment Completed
            </h2>
            <p style={{ color: "#667085", fontSize: "0.9375rem", marginBottom: "1.5rem" }}>
              Compiling topic evaluation metrics...
            </p>
            <div style={{ color: "#315EA8", fontWeight: "600", fontSize: "0.875rem" }}>
              Loading Technical Evaluation Dashboard
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
    gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
    gap: "1rem",
    padding: "1rem 1.25rem",
    background: "#FFFFFF",
    borderRadius: "8px",
    border: "1px solid #E2E4E7",
  },
  hudItem: {
    display: "flex",
    flexDirection: "column",
    gap: "0.15rem",
  },
  hudLabel: {
    fontSize: "0.75rem",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    color: "#667085",
  },
  hudValue: {
    fontSize: "0.9375rem",
    fontWeight: "600",
    color: "#111827",
  },
};

export default function InterviewPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: "center", padding: "4rem", color: "#667085" }}>Loading assessment room...</div>}>
      <TechnicalInterviewContent />
    </Suspense>
  );
}
