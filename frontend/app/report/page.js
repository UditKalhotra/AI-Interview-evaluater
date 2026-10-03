"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Navbar from "../components/Navbar";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function AssessmentReportContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");

  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedQuestion, setExpandedQuestion] = useState(null);

  const fetchReport = async (forceRefresh = false) => {
    if (!sessionId) {
      setError("No session_id provided in URL");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const url = `${API_URL}/interview/session/${encodeURIComponent(sessionId)}/report${
        forceRefresh ? "?refresh=true" : ""
      }`;
      const res = await fetch(url);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Failed to fetch report (status ${res.status})`);
      }

      const data = await res.json();
      setReport(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport(false);
  }, [sessionId]);

  const handleStartNew = () => {
    router.push("/");
  };

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#0b0f19" }}>
        <Navbar />
        <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
          <div style={{ textAlign: "center", padding: "3rem" }}>
            <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⏳</div>
            <h3 style={{ color: "#f8fafc", marginBottom: "0.5rem" }}>Generating Assessment Report...</h3>
            <p style={{ fontSize: "0.9rem", color: "#64748b" }}>
              Calculating IRT ability parameters, LSA semantic coverage, and speech features.
            </p>
          </div>
        </main>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#0b0f19" }}>
        <Navbar />
        <main style={{ flex: 1, padding: "3rem 1.5rem", maxWidth: "700px", margin: "0 auto", textAlign: "center" }}>
          <div style={{ padding: "2.5rem", background: "#151d2a", borderRadius: "16px", border: "1px solid #ef4444" }}>
            <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>⚠️</div>
            <h2 style={{ color: "#ef4444", marginBottom: "0.5rem" }}>Could Not Load Report</h2>
            <p style={{ color: "#94a3b8", marginBottom: "1.5rem" }}>{error || "Report unavailable"}</p>
            <div style={{ display: "flex", gap: "1rem", justifyContent: "center" }}>
              <button
                onClick={() => fetchReport(true)}
                style={{
                  padding: "0.75rem 1.5rem",
                  borderRadius: "10px",
                  background: "#2563eb",
                  color: "#ffffff",
                  border: "none",
                  cursor: "pointer",
                  fontWeight: "600",
                }}
              >
                🔄 Recompute Report
              </button>
              <button
                onClick={handleStartNew}
                style={{
                  padding: "0.75rem 1.5rem",
                  borderRadius: "10px",
                  background: "#0f1724",
                  border: "1px solid #233044",
                  color: "#ffffff",
                  cursor: "pointer",
                  fontWeight: "600",
                }}
              >
                🏠 Return Home
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  const {
    overall_technical_score = 0,
    overall_communication_score = 0,
    overall_score = 0,
    final_theta = 0,
    standard_error = 1,
    total_questions_answered = 0,
    per_question_breakdown = [],
    topic_breakdown = [],
    strengths = [],
    weaknesses = [],
  } = report;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#0b0f19" }}>
      <Navbar />

      <main style={{ flex: 1, padding: "2.5rem 1.5rem", maxWidth: "1100px", margin: "0 auto", width: "100%" }}>
        {/* Top Header */}
        <div style={styles.topHeader}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.4rem" }}>
              <h1 style={{ fontSize: "2rem", fontWeight: "800", color: "#f8fafc", margin: 0 }}>
                Candidate Evaluation Report
              </h1>
              <span style={styles.completedBadge}>
                Assessment Completed
              </span>
            </div>
            <div style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
              Session ID: <code style={{ color: "#60a5fa" }}>{sessionId}</code> • Answered {total_questions_answered} Questions
            </div>
          </div>

          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <button onClick={() => fetchReport(true)} style={styles.btnSecondary}>
              🔄 Recompute
            </button>
            <button onClick={handleStartNew} style={styles.btnPrimary}>
              🚀 Start New Assessment
            </button>
          </div>
        </div>

        {/* Summary Metric Cards */}
        <div style={styles.scoreGrid}>
          {/* Technical Accuracy */}
          <div style={styles.scoreCard}>
            <div style={styles.cardHeaderLabel}>Technical Score</div>
            <div style={{ ...styles.cardValue, color: "#3b82f6" }}>
              {overall_technical_score.toFixed(1)}%
            </div>
            <div style={styles.track}>
              <div style={{ ...styles.fill, width: `${Math.min(100, overall_technical_score)}%`, background: "#3b82f6" }} />
            </div>
            <div style={styles.cardSubtext}>LSA semantic rubric evaluation</div>
          </div>

          {/* Communication Score */}
          <div style={styles.scoreCard}>
            <div style={styles.cardHeaderLabel}>Communication Score</div>
            <div style={{ ...styles.cardValue, color: "#8b5cf6" }}>
              {overall_communication_score.toFixed(1)}%
            </div>
            <div style={styles.track}>
              <div style={{ ...styles.fill, width: `${Math.min(100, overall_communication_score)}%`, background: "#8b5cf6" }} />
            </div>
            <div style={styles.cardSubtext}>Gemini speech delivery & clarity</div>
          </div>

          {/* Overall Composite */}
          <div style={styles.scoreCard}>
            <div style={styles.cardHeaderLabel}>Combined Overall</div>
            <div style={{ ...styles.cardValue, color: "#10b981" }}>
              {overall_score.toFixed(1)}%
            </div>
            <div style={styles.track}>
              <div style={{ ...styles.fill, width: `${Math.min(100, overall_score)}%`, background: "#10b981" }} />
            </div>
            <div style={styles.cardSubtext}>70% Technical + 30% Communication</div>
          </div>

          {/* IRT Ability Theta */}
          <div style={styles.scoreCard}>
            <div style={styles.cardHeaderLabel}>IRT Ability Level (\(\theta\))</div>
            <div style={{ ...styles.cardValue, color: "#f59e0b" }}>
              {final_theta >= 0 ? `+${final_theta.toFixed(2)}` : final_theta.toFixed(2)}
            </div>
            <div style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
              Std Error: <strong style={{ color: "#f8fafc" }}>{standard_error.toFixed(2)}</strong>
            </div>
            <div style={styles.cardSubtext}>1PL/2PL latent ability estimation</div>
          </div>
        </div>

        {/* Strengths & Areas for Improvement */}
        <div style={styles.feedbackGrid}>
          {/* Strengths */}
          <div style={{ ...styles.feedbackCard, borderColor: "rgba(16, 185, 129, 0.25)" }}>
            <div style={styles.feedbackHeader}>
              <span style={{ fontSize: "1.2rem" }}>🌟</span>
              <h3 style={{ margin: 0, color: "#10b981", fontSize: "1.1rem" }}>Demonstrated Strengths</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {strengths.map((str, idx) => (
                <div key={idx} style={styles.strengthBox}>
                  {str}
                </div>
              ))}
            </div>
          </div>

          {/* Weaknesses */}
          <div style={{ ...styles.feedbackCard, borderColor: "rgba(245, 158, 11, 0.25)" }}>
            <div style={styles.feedbackHeader}>
              <span style={{ fontSize: "1.2rem" }}>🎯</span>
              <h3 style={{ margin: 0, color: "#f59e0b", fontSize: "1.1rem" }}>Areas for Improvement</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {weaknesses.map((wk, idx) => (
                <div key={idx} style={styles.weaknessBox}>
                  {wk}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Topic Breakdown Section */}
        <div style={styles.sectionBox}>
          <h3 style={styles.sectionHeaderTitle}>Topic Mastery Breakdown</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {topic_breakdown.map((t, idx) => (
              <div key={idx} style={styles.topicRow}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                  <div>
                    <span style={{ fontWeight: "700", color: "#f8fafc", fontSize: "1rem" }}>{t.topic}</span>
                    <span style={{ color: "#64748b", fontSize: "0.8rem", marginLeft: "0.5rem" }}>
                      ({t.question_count} Question{t.question_count > 1 ? "s" : ""})
                    </span>
                  </div>
                  <div style={{ fontWeight: "700", color: "#10b981", fontSize: "1.05rem" }}>
                    Combined: {t.avg_combined_score.toFixed(1)}%
                  </div>
                </div>

                <div style={{ marginBottom: "0.5rem" }}>
                  <div style={styles.subBarLabel}>
                    <span>Technical Correctness</span>
                    <span>{t.avg_correctness_score.toFixed(1)}%</span>
                  </div>
                  <div style={styles.track}>
                    <div style={{ ...styles.fill, width: `${Math.min(100, t.avg_correctness_score)}%`, background: "#3b82f6" }} />
                  </div>
                </div>

                <div>
                  <div style={styles.subBarLabel}>
                    <span>Communication Delivery</span>
                    <span>{t.avg_behavior_score.toFixed(1)}%</span>
                  </div>
                  <div style={styles.track}>
                    <div style={{ ...styles.fill, width: `${Math.min(100, t.avg_behavior_score)}%`, background: "#8b5cf6" }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Per-Question Detailed Breakdown */}
        <div style={{ ...styles.sectionBox, marginTop: "2rem" }}>
          <h3 style={styles.sectionHeaderTitle}>Per-Question Assessment Log</h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {per_question_breakdown.map((q, idx) => {
              const isExpanded = expandedQuestion === idx;
              return (
                <div key={idx} style={styles.questionAccordionItem}>
                  <div
                    onClick={() => setExpandedQuestion(isExpanded ? null : idx)}
                    style={styles.accordionHeader}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                      <span style={{ fontWeight: "700", color: "#3b82f6" }}>Q{idx + 1}</span>
                      <span style={{ fontWeight: "600", color: "#f8fafc" }}>{q.question_id}</span>
                      <span style={styles.tagTopic}>{q.topic}</span>
                      <span style={styles.tagDiff}>
                        {q.difficulty} (IRT b: {q.irt_difficulty})
                      </span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ color: "#3b82f6", fontWeight: "700", fontSize: "0.95rem" }}>
                          Tech: {q.correctness_score !== null ? `${q.correctness_score}%` : "N/A"}
                        </div>
                        <div style={{ color: "#8b5cf6", fontSize: "0.8rem" }}>
                          Speech: {q.behavior_score !== null ? `${q.behavior_score}%` : "N/A"}
                        </div>
                      </div>
                      <span style={{ color: "#64748b", fontSize: "1rem" }}>
                        {isExpanded ? "▲" : "▼"}
                      </span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div style={styles.accordionBody}>
                      <div>
                        <div style={styles.fieldLabel}>Question Statement</div>
                        <div style={{ color: "#f8fafc", fontSize: "0.95rem", lineHeight: "1.5" }}>
                          {q.question_text}
                        </div>
                      </div>

                      <div>
                        <div style={styles.fieldLabel}>Candidate Spoken Transcript</div>
                        <div style={styles.transcriptBox}>
                          "{q.transcript || "(No transcript recorded)"}"
                        </div>
                      </div>

                      {q.features && (
                        <div style={styles.featuresRow}>
                          <span>⏱️ Response Latency: <strong style={{ color: "#f8fafc" }}>{q.response_time_seconds}s</strong></span>
                          <span>🗣️ Fillers: <strong style={{ color: "#f8fafc" }}>{q.features.fillers ?? 0}</strong></span>
                          <span>⚡ Speaking Rate: <strong style={{ color: "#f8fafc" }}>{q.features.speaking_rate ? `${q.features.speaking_rate.toFixed(0)} WPM` : "N/A"}</strong></span>
                        </div>
                      )}

                      {q.behavior_explanation && (
                        <div>
                          <div style={styles.fieldLabel}>Communication Evaluation</div>
                          <div style={{ color: "#cbd5e1", fontSize: "0.9rem", lineHeight: "1.5" }}>
                            {q.behavior_explanation}
                          </div>
                        </div>
                      )}

                      {q.missed_rubric_points && q.missed_rubric_points.length > 0 && (
                        <div>
                          <div style={{ ...styles.fieldLabel, color: "#f59e0b" }}>Missed Rubric Concepts</div>
                          <ul style={{ margin: 0, paddingLeft: "1.25rem", color: "#cbd5e1", fontSize: "0.875rem" }}>
                            {q.missed_rubric_points.map((m, mIdx) => (
                              <li key={mIdx}>{m}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}

const styles = {
  topHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "1rem",
    marginBottom: "2rem",
    paddingBottom: "1.5rem",
    borderBottom: "1px solid #233044",
  },
  completedBadge: {
    padding: "0.25rem 0.75rem",
    borderRadius: "9999px",
    background: "rgba(16, 185, 129, 0.12)",
    color: "#10b981",
    border: "1px solid rgba(16, 185, 129, 0.3)",
    fontSize: "0.8rem",
    fontWeight: "600",
  },
  btnPrimary: {
    padding: "0.65rem 1.35rem",
    borderRadius: "10px",
    background: "#2563eb",
    color: "#ffffff",
    border: "none",
    fontWeight: "600",
    fontSize: "0.9rem",
    cursor: "pointer",
  },
  btnSecondary: {
    padding: "0.65rem 1.25rem",
    borderRadius: "10px",
    background: "#151d2a",
    color: "#cbd5e1",
    border: "1px solid #233044",
    fontWeight: "600",
    fontSize: "0.9rem",
    cursor: "pointer",
  },
  scoreGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "1.25rem",
    marginBottom: "2.5rem",
  },
  scoreCard: {
    background: "#151d2a",
    borderRadius: "14px",
    padding: "1.5rem",
    border: "1px solid #233044",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
  },
  cardHeaderLabel: {
    color: "#94a3b8",
    fontSize: "0.8rem",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  cardValue: {
    fontSize: "2.25rem",
    fontWeight: "800",
    margin: "0.4rem 0",
  },
  cardSubtext: {
    color: "#64748b",
    fontSize: "0.775rem",
    marginTop: "0.5rem",
  },
  track: {
    width: "100%",
    height: "6px",
    background: "#0f1724",
    borderRadius: "3px",
    overflow: "hidden",
  },
  fill: {
    height: "100%",
    borderRadius: "3px",
  },
  feedbackGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
    gap: "1.5rem",
    marginBottom: "2.5rem",
  },
  feedbackCard: {
    background: "#151d2a",
    borderRadius: "14px",
    padding: "1.5rem",
    border: "1px solid #233044",
  },
  feedbackHeader: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    marginBottom: "1rem",
  },
  strengthBox: {
    padding: "0.75rem 1rem",
    background: "rgba(16, 185, 129, 0.08)",
    borderRadius: "8px",
    borderLeft: "3px solid #10b981",
    color: "#e2e8f0",
    fontSize: "0.9rem",
    lineHeight: "1.5",
  },
  weaknessBox: {
    padding: "0.75rem 1rem",
    background: "rgba(245, 158, 11, 0.08)",
    borderRadius: "8px",
    borderLeft: "3px solid #f59e0b",
    color: "#e2e8f0",
    fontSize: "0.9rem",
    lineHeight: "1.5",
  },
  sectionBox: {
    background: "#151d2a",
    borderRadius: "16px",
    padding: "1.75rem",
    border: "1px solid #233044",
  },
  sectionHeaderTitle: {
    fontSize: "1.2rem",
    fontWeight: "700",
    color: "#f8fafc",
    marginBottom: "1.25rem",
  },
  topicRow: {
    background: "#0f1724",
    padding: "1.25rem",
    borderRadius: "12px",
    border: "1px solid #233044",
  },
  subBarLabel: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: "0.8rem",
    color: "#94a3b8",
    marginBottom: "0.25rem",
  },
  questionAccordionItem: {
    background: "#0f1724",
    borderRadius: "12px",
    border: "1px solid #233044",
    overflow: "hidden",
  },
  accordionHeader: {
    padding: "1.25rem",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    cursor: "pointer",
    background: "#0f1724",
    transition: "background 0.2s ease",
  },
  tagTopic: {
    fontSize: "0.75rem",
    padding: "0.2rem 0.6rem",
    borderRadius: "6px",
    background: "#233044",
    color: "#94a3b8",
  },
  tagDiff: {
    fontSize: "0.75rem",
    padding: "0.2rem 0.6rem",
    borderRadius: "6px",
    background: "rgba(37, 99, 235, 0.12)",
    color: "#60a5fa",
  },
  accordionBody: {
    padding: "1.25rem",
    borderTop: "1px solid #233044",
    display: "flex",
    flexDirection: "column",
    gap: "1.25rem",
  },
  fieldLabel: {
    color: "#64748b",
    fontSize: "0.75rem",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    marginBottom: "0.35rem",
  },
  transcriptBox: {
    padding: "0.75rem 1rem",
    background: "#151d2a",
    borderRadius: "8px",
    color: "#cbd5e1",
    fontStyle: "italic",
    fontSize: "0.9rem",
    lineHeight: "1.5",
  },
  featuresRow: {
    display: "flex",
    gap: "1.25rem",
    flexWrap: "wrap",
    fontSize: "0.85rem",
    color: "#94a3b8",
  },
};

export default function AssessmentReportPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: "center", padding: "4rem", color: "#94a3b8" }}>Loading report dashboard...</div>}>
      <AssessmentReportContent />
    </Suspense>
  );
}
