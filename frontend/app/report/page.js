"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Navbar from "../components/Navbar";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function AssessmentReportContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");

  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedQuestions, setExpandedQuestions] = useState({});
  const [allExpanded, setAllExpanded] = useState(false);

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

  const toggleExpandAll = () => {
    if (!report || !report.per_question_breakdown) return;
    const nextState = !allExpanded;
    setAllExpanded(nextState);
    const newExpanded = {};
    if (nextState) {
      report.per_question_breakdown.forEach((_, idx) => {
        newExpanded[idx] = true;
      });
    }
    setExpandedQuestions(newExpanded);
  };

  const toggleQuestion = (idx) => {
    setExpandedQuestions((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  const handleStartNew = () => {
    router.push("/");
  };

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <Navbar />
        <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ textAlign: "center", padding: "3rem", background: "#FFFFFF", borderRadius: "16px", border: "1px solid #E2E7EF", boxShadow: "0 4px 20px rgba(30, 60, 90, 0.05)" }}>
            <div style={{ width: "40px", height: "40px", border: "4px solid #EAF2FF", borderTop: "4px solid #2F66C5", borderRadius: "50%", margin: "0 auto 1rem", animation: "spin 1s linear infinite" }} />
            <h3 style={{ color: "#102A43", marginBottom: "0.5rem", fontWeight: "700", fontSize: "1.15rem" }}>Generating Assessment Results</h3>
            <p style={{ fontSize: "0.875rem", color: "#5E7187" }}>
              Evaluating LSA technical scores, communication delivery, and key takeaways.
            </p>
          </div>
        </main>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <Navbar />
        <main style={{ flex: 1, padding: "3rem 1.5rem", maxWidth: "650px", margin: "0 auto", textAlign: "center" }}>
          <div style={{ padding: "2.5rem", background: "#FFFFFF", borderRadius: "16px", border: "1px solid #ECC6C6", boxShadow: "0 4px 20px rgba(30, 60, 90, 0.05)" }}>
            <h2 style={{ color: "#D35D5D", marginBottom: "0.5rem", fontWeight: "700", fontSize: "1.25rem" }}>Could Not Load Assessment Report</h2>
            <p style={{ color: "#5E7187", marginBottom: "1.5rem", fontSize: "0.875rem" }}>{error || "Report data is unavailable"}</p>
            <div style={{ display: "flex", gap: "0.85rem", justifyContent: "center" }}>
              <button onClick={() => fetchReport(true)} className="btn-secondary" style={{ padding: "0.6rem 1.25rem", borderRadius: "8px", fontWeight: "600", fontSize: "0.875rem" }}>
                Refresh Report
              </button>
              <button onClick={handleStartNew} className="btn-primary" style={{ padding: "0.6rem 1.25rem", borderRadius: "8px", fontWeight: "600", fontSize: "0.875rem" }}>
                Return to Topics
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  const {
    topic: sessionTopic = "General",
    overall_technical_score = 0,
    overall_communication_score = 0,
    overall_score = 0,
    total_questions_answered = 0,
    per_question_breakdown = [],
    strengths = [],
    weaknesses = [],
    next_steps = [],
    created_at = null,
  } = report;

  const totalQ = per_question_breakdown.length || total_questions_answered || 1;
  const strongCount = per_question_breakdown.filter((q) => (q.correctness_score ?? 0) >= 70).length;
  const partialCount = per_question_breakdown.filter((q) => (q.correctness_score ?? 0) >= 40 && (q.correctness_score ?? 0) < 70).length;
  const needsReviewCount = per_question_breakdown.filter((q) => (q.correctness_score ?? 0) < 40).length;

  const strongPct = Math.round((strongCount / totalQ) * 100);
  const partialPct = Math.round((partialCount / totalQ) * 100);
  const needsReviewPct = Math.round((needsReviewCount / totalQ) * 100);

  // Date formatting matching reference
  const formattedDate = created_at
    ? new Date(created_at).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" })
    : new Date().toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });

  // Format weak question labels for Key Takeaways & Next Steps
  const weakQIndices = per_question_breakdown
    .map((q, idx) => ((q.correctness_score ?? 0) < 40 ? `Q${idx + 1}` : null))
    .filter(Boolean);
  const weakQText = weakQIndices.length > 0 ? weakQIndices.join(", ") : "low-scoring questions";

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Navbar />

      <main style={{ flex: 1, padding: "2rem 1.5rem 4rem", maxWidth: "1240px", margin: "0 auto", width: "100%" }}>
        {/* Top Navigation & Header */}
        <div style={{ marginBottom: "1.75rem" }}>
          <Link
            href="/"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              color: "#5E7187",
              fontSize: "0.875rem",
              fontWeight: "600",
              textDecoration: "none",
              marginBottom: "0.75rem",
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            Back to Topics
          </Link>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: "1rem" }}>
            <div>
              <h1 style={{ fontSize: "2.25rem", fontWeight: "800", color: "#102A43", margin: "0 0 0.4rem 0", letterSpacing: "-0.02em" }}>
                Technical Assessment Results
              </h1>
              <div style={{ color: "#5E7187", fontSize: "0.9375rem" }}>
                {sessionTopic} · {total_questions_answered} question{total_questions_answered !== 1 ? "s" : ""} completed · <span style={{ color: "#829AB1" }}>{formattedDate}</span>
              </div>
            </div>

            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button
                onClick={() => fetchReport(true)}
                className="btn-secondary"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  padding: "0.65rem 1.15rem",
                  borderRadius: "10px",
                  fontWeight: "600",
                  fontSize: "0.875rem",
                }}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M23 4v6h-6M1 20v-6h6"/>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                </svg>
                Refresh Report
              </button>
              <button
                onClick={handleStartNew}
                className="btn-primary"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  padding: "0.65rem 1.25rem",
                  borderRadius: "10px",
                  fontWeight: "600",
                  fontSize: "0.875rem",
                }}
              >
                Select New Topic →
              </button>
            </div>
          </div>
        </div>

        {/* 3 TOP SCORE METRIC CARDS (Exact match to Reference 2) */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem", marginBottom: "1.75rem" }}>
          {/* Technical Score */}
          <div style={{ background: "#EAF2FF", border: "1px solid #D0E1FD", borderRadius: "16px", padding: "1.35rem 1.5rem", position: "relative" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <div style={{ width: "44px", height: "44px", borderRadius: "12px", background: "#3267C8", display: "flex", alignItems: "center", justifyContent: "center", color: "#FFFFFF", flexShrink: 0 }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="20" x2="18" y2="10" />
                  <line x1="12" y1="20" x2="12" y2="4" />
                  <line x1="6" y1="20" x2="6" y2="14" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: "0.8125rem", fontWeight: "700", color: "#5E7187", textTransform: "none", marginBottom: "0.15rem" }}>
                  Technical Score
                </div>
                <div style={{ fontSize: "2.25rem", fontWeight: "800", color: "#102A43", lineHeight: "1.1" }}>
                  {overall_technical_score.toFixed(1)}%
                </div>
                <div style={{ fontSize: "0.78125rem", color: "#5E7187", marginTop: "0.25rem" }}>
                  LSA semantic evaluation
                </div>
              </div>
            </div>
          </div>

          {/* Communication Score */}
          <div style={{ background: "#FDEEEF", border: "1px solid #FCD3D7", borderRadius: "16px", padding: "1.35rem 1.5rem", position: "relative" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <div style={{ width: "44px", height: "44px", borderRadius: "12px", background: "#D35D5D", display: "flex", alignItems: "center", justifyContent: "center", color: "#FFFFFF", flexShrink: 0 }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                  <line x1="12" y1="19" x2="12" y2="23"/>
                  <line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
              </div>
              <div>
                <div style={{ fontSize: "0.8125rem", fontWeight: "700", color: "#5E7187", textTransform: "none", marginBottom: "0.15rem" }}>
                  Communication Score
                </div>
                <div style={{ fontSize: "2.25rem", fontWeight: "800", color: "#102A43", lineHeight: "1.1" }}>
                  {overall_communication_score.toFixed(1)}%
                </div>
                <div style={{ fontSize: "0.78125rem", color: "#5E7187", marginTop: "0.25rem" }}>
                  Speech delivery & clarity
                </div>
              </div>
            </div>
          </div>

          {/* Overall Score */}
          <div style={{ background: "#EAF7F0", border: "1px solid #C6ECD5", borderRadius: "16px", padding: "1.35rem 1.5rem", position: "relative" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <div style={{ width: "44px", height: "44px", borderRadius: "12px", background: "#3D9468", display: "flex", alignItems: "center", justifyContent: "center", color: "#FFFFFF", flexShrink: 0 }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: "0.8125rem", fontWeight: "700", color: "#5E7187", textTransform: "none", marginBottom: "0.15rem" }}>
                  Overall Score
                </div>
                <div style={{ fontSize: "2.25rem", fontWeight: "800", color: "#102A43", lineHeight: "1.1" }}>
                  {overall_score.toFixed(1)}%
                </div>
                <div style={{ fontSize: "0.78125rem", color: "#5E7187", marginTop: "0.25rem" }}>
                  Composite assessment score
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* MAIN DASHBOARD 2-COLUMN GRID (Matching Reference 2 layout) */}
        <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: "1.5rem", alignItems: "start" }}>

          {/* LEFT COLUMN: Charts & Question Details */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>

            {/* 1. TECHNICAL PERFORMANCE BY QUESTION (Bar Chart) */}
            <div className="card-white" style={{ padding: "1.5rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.25rem" }}>
                <div style={{ width: "28px", height: "28px", borderRadius: "8px", background: "#EAF2FF", display: "flex", alignItems: "center", justifyContent: "center", color: "#2F66C5" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="20" x2="18" y2="10" />
                    <line x1="12" y1="20" x2="12" y2="4" />
                    <line x1="6" y1="20" x2="6" y2="14" />
                  </svg>
                </div>
                <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#102A43", margin: 0 }}>
                  Technical Performance by Question
                </h2>
              </div>
              <p style={{ color: "#5E7187", fontSize: "0.8125rem", margin: "0 0 1.5rem 2.3rem" }}>
                Individual technical scores for each question
              </p>

              {/* Bar Chart Area */}
              <div style={{ padding: "0 0.5rem" }}>
                <div style={{ position: "relative", height: "180px", display: "flex", alignItems: "flex-end", justifyContent: "space-between", paddingBottom: "24px", borderBottom: "1px solid #E2E7EF" }}>
                  {/* Horizontal Grid lines */}
                  <div style={{ position: "absolute", top: 0, left: 0, right: 0, borderTop: "1px dashed #E2E7EF", height: 0 }}>
                    <span style={{ position: "absolute", left: "-32px", top: "-8px", fontSize: "0.7rem", color: "#829AB1" }}>100%</span>
                  </div>
                  <div style={{ position: "absolute", top: "20%", left: 0, right: 0, borderTop: "1px dashed #E2E7EF", height: 0 }}>
                    <span style={{ position: "absolute", left: "-32px", top: "-8px", fontSize: "0.7rem", color: "#829AB1" }}>80%</span>
                  </div>
                  <div style={{ position: "absolute", top: "40%", left: 0, right: 0, borderTop: "1px dashed #E2E7EF", height: 0 }}>
                    <span style={{ position: "absolute", left: "-32px", top: "-8px", fontSize: "0.7rem", color: "#829AB1" }}>60%</span>
                  </div>
                  <div style={{ position: "absolute", top: "60%", left: 0, right: 0, borderTop: "1px dashed #E2E7EF", height: 0 }}>
                    <span style={{ position: "absolute", left: "-32px", top: "-8px", fontSize: "0.7rem", color: "#829AB1" }}>40%</span>
                  </div>
                  <div style={{ position: "absolute", top: "80%", left: 0, right: 0, borderTop: "1px dashed #E2E7EF", height: 0 }}>
                    <span style={{ position: "absolute", left: "-32px", top: "-8px", fontSize: "0.7rem", color: "#829AB1" }}>20%</span>
                  </div>
                  <div style={{ position: "absolute", bottom: "24px", left: 0, right: 0, borderTop: "1px solid #E2E7EF", height: 0 }}>
                    <span style={{ position: "absolute", left: "-32px", top: "-8px", fontSize: "0.7rem", color: "#829AB1" }}>0%</span>
                  </div>

                  {/* Bars */}
                  {per_question_breakdown.map((q, idx) => {
                    const techScore = q.correctness_score ?? 0;
                    const barHeightPct = Math.max(3, Math.min(100, techScore));
                    return (
                      <div key={idx} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", height: "100%", zIndex: 1, padding: "0 10px" }}>
                        {/* Percentage label above bar */}
                        <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#102A43", marginBottom: "4px" }}>
                          {techScore.toFixed(0)}%
                        </span>
                        {/* Bar element */}
                        <div
                          style={{
                            width: "100%",
                            maxWidth: "42px",
                            height: `${barHeightPct}%`,
                            background: "linear-gradient(180deg, #5B8DEF 0%, #3267C8 100%)",
                            borderRadius: "6px 6px 0 0",
                            transition: "height 0.4s ease",
                          }}
                        />
                      </div>
                    );
                  })}
                </div>

                {/* X-axis Labels */}
                <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "8px" }}>
                  {per_question_breakdown.map((_, idx) => (
                    <div key={idx} style={{ flex: 1, textAlign: "center", fontSize: "0.8125rem", fontWeight: "700", color: "#5E7187" }}>
                      Q{idx + 1}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* 2. QUESTION DETAILS ACCORDION */}
            <div className="card-white" style={{ padding: "1.5rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                  <div style={{ width: "28px", height: "28px", borderRadius: "8px", background: "#EAF2FF", display: "flex", alignItems: "center", justifyContent: "center", color: "#2F66C5" }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="8" y1="6" x2="21" y2="6"/>
                      <line x1="8" y1="12" x2="21" y2="12"/>
                      <line x1="8" y1="18" x2="21" y2="18"/>
                      <line x1="3" y1="6" x2="3.01" y2="6"/>
                      <line x1="3" y1="12" x2="3.01" y2="12"/>
                      <line x1="3" y1="18" x2="3.01" y2="18"/>
                    </svg>
                  </div>
                  <div>
                    <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#102A43", margin: 0 }}>
                      Question Details
                    </h2>
                    <p style={{ color: "#5E7187", fontSize: "0.8125rem", margin: 0 }}>
                      Detailed performance for each question
                    </p>
                  </div>
                </div>

                <button
                  onClick={toggleExpandAll}
                  style={{
                    background: "#F8F9FC",
                    border: "1px solid #E2E7EF",
                    borderRadius: "8px",
                    padding: "0.4rem 0.85rem",
                    fontSize: "0.8125rem",
                    fontWeight: "600",
                    color: "#2F66C5",
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.3rem",
                  }}
                >
                  {allExpanded ? "Collapse All" : "Expand All"}
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points={allExpanded ? "18 15 12 9 6 15" : "6 9 12 15 18 9"} />
                  </svg>
                </button>
              </div>

              {/* Rows List */}
              <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                {per_question_breakdown.map((q, idx) => {
                  const isOpen = !!expandedQuestions[idx];
                  const techScore = q.correctness_score ?? 0;
                  const commScore = q.behavior_score ?? 0;

                  const statusText = q.status || (techScore >= 70 ? "Strong" : techScore >= 40 ? "Partial" : "Needs Review");
                  const badgeBg = techScore >= 70 ? "#EAF7F0" : techScore >= 40 ? "#FFF7DF" : "#FDEEEF";
                  const badgeColor = techScore >= 70 ? "#3D9468" : techScore >= 40 ? "#C58A27" : "#D35D5D";

                  return (
                    <div
                      key={idx}
                      style={{
                        border: "1px solid #E2E7EF",
                        borderRadius: "12px",
                        overflow: "hidden",
                        background: isOpen ? "#FAFBFD" : "#FFFFFF",
                        transition: "all 0.2s ease",
                      }}
                    >
                      {/* Accordion Row Header */}
                      <div
                        onClick={() => toggleQuestion(idx)}
                        style={{
                          padding: "0.9rem 1.15rem",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          cursor: "pointer",
                          userSelect: "none",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "0.85rem" }}>
                          <span style={{ fontWeight: "800", color: "#2F66C5", fontSize: "0.9375rem" }}>
                            Q{idx + 1}
                          </span>
                          <span style={{ fontSize: "0.8125rem", color: "#5E7187", background: "#F7F8FA", padding: "0.2rem 0.6rem", borderRadius: "6px", border: "1px solid #E2E7EF" }}>
                            {q.difficulty || "Medium"}
                          </span>
                          <span
                            style={{
                              fontSize: "0.78125rem",
                              fontWeight: "700",
                              padding: "0.2rem 0.65rem",
                              borderRadius: "6px",
                              background: badgeBg,
                              color: badgeColor,
                            }}
                          >
                            {statusText}
                          </span>
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
                          <div style={{ fontSize: "0.84375rem", color: "#5E7187" }}>
                            Tech <strong style={{ color: "#102A43", fontWeight: "700" }}>{techScore.toFixed(0)}%</strong>
                            <span style={{ margin: "0 0.5rem", color: "#D0D7DE" }}>·</span>
                            Comm <strong style={{ color: "#102A43", fontWeight: "700" }}>{commScore.toFixed(0)}%</strong>
                          </div>
                          <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="#5E7187"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            style={{ transform: isOpen ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s ease" }}
                          >
                            <polyline points="6 9 12 15 18 9" />
                          </svg>
                        </div>
                      </div>

                      {/* Accordion Expanded Details */}
                      {isOpen && (
                        <div style={{ padding: "1.15rem", borderTop: "1px solid #E2E7EF", background: "#FFFFFF", display: "flex", flexDirection: "column", gap: "0.9rem" }}>
                          <div>
                            <div style={{ fontSize: "0.75rem", fontWeight: "700", color: "#5E7187", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "0.3rem" }}>
                              Question Statement
                            </div>
                            <div style={{ color: "#102A43", fontSize: "0.9375rem", fontWeight: "600", lineHeight: "1.4" }}>
                              {q.question_text}
                            </div>
                          </div>

                          <div>
                            <div style={{ fontSize: "0.75rem", fontWeight: "700", color: "#5E7187", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "0.3rem" }}>
                              Candidate Spoken Response
                            </div>
                            <div style={{ padding: "0.75rem 1rem", background: "#F8F9FC", borderRadius: "8px", border: "1px solid #E2E7EF", color: "#102A43", fontSize: "0.875rem", fontStyle: "italic", lineHeight: "1.5" }}>
                              "{q.transcript || "(No audio transcript captured)"}"
                            </div>
                          </div>

                          {q.features && (
                            <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap", fontSize: "0.8125rem", color: "#5E7187", background: "#F7F8FA", padding: "0.6rem 0.85rem", borderRadius: "8px" }}>
                              <span>Response Latency: <strong style={{ color: "#102A43" }}>{q.response_time_seconds}s</strong></span>
                              <span>Filler Count: <strong style={{ color: "#102A43" }}>{q.features.fillers ?? 0}</strong></span>
                              <span>Speaking Pace: <strong style={{ color: "#102A43" }}>{q.features.speaking_rate ? `${q.features.speaking_rate.toFixed(0)} WPM` : "N/A"}</strong></span>
                            </div>
                          )}

                          {q.behavior_explanation && (
                            <div>
                              <div style={{ fontSize: "0.75rem", fontWeight: "700", color: "#5E7187", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "0.2rem" }}>
                                Speech Delivery Feedback
                              </div>
                              <div style={{ color: "#5E7187", fontSize: "0.8125rem", lineHeight: "1.4" }}>
                                {q.behavior_explanation}
                              </div>
                            </div>
                          )}

                          {q.missed_rubric_points && q.missed_rubric_points.length > 0 && (
                            <div style={{ background: "#FFF7DF", border: "1px solid #FCE4A6", borderRadius: "8px", padding: "0.75rem 1rem" }}>
                              <div style={{ fontSize: "0.75rem", fontWeight: "700", color: "#C58A27", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "0.3rem" }}>
                                Missed Key Technical Concepts
                              </div>
                              <ul style={{ margin: 0, paddingLeft: "1.2rem", color: "#5E7187", fontSize: "0.8125rem", lineHeight: "1.5" }}>
                                {q.missed_rubric_points.map((pt, pIdx) => (
                                  <li key={pIdx}>{pt}</li>
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

          </div>

          {/* RIGHT COLUMN: Performance Breakdown Donut, Key Takeaways & Next Steps */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>

            {/* 1. PERFORMANCE BREAKDOWN (Donut Chart matching Reference 2) */}
            <div className="card-white" style={{ padding: "1.5rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.25rem" }}>
                <div style={{ width: "28px", height: "28px", borderRadius: "8px", background: "#EAF2FF", display: "flex", alignItems: "center", justifyContent: "center", color: "#2F66C5" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
                    <path d="M22 12A10 10 0 0 0 12 2v10z" />
                  </svg>
                </div>
                <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#102A43", margin: 0 }}>
                  Performance Breakdown
                </h2>
              </div>
              <p style={{ color: "#5E7187", fontSize: "0.8125rem", margin: "0 0 1.25rem 2.3rem" }}>
                Distribution of responses by technical score
              </p>

              <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
                {/* SVG Donut */}
                <div style={{ position: "relative", width: "110px", height: "110px", flexShrink: 0 }}>
                  <svg width="110" height="110" viewBox="0 0 36 36" style={{ transform: "rotate(-90deg)" }}>
                    {/* Background Ring */}
                    <circle cx="18" cy="18" r="14.5" fill="none" stroke="#FDEEEF" strokeWidth="4.5" />
                    {/* Partial Ring */}
                    {partialPct > 0 && (
                      <circle
                        cx="18"
                        cy="18"
                        r="14.5"
                        fill="none"
                        stroke="#FFF7DF"
                        strokeWidth="4.5"
                        strokeDasharray={`${partialPct} 100`}
                        strokeDashoffset={`-${strongPct}`}
                      />
                    )}
                    {/* Strong Ring */}
                    {strongPct > 0 && (
                      <circle
                        cx="18"
                        cy="18"
                        r="14.5"
                        fill="none"
                        stroke="#EAF7F0"
                        strokeWidth="4.5"
                        strokeDasharray={`${strongPct} 100`}
                        strokeDashoffset="0"
                      />
                    )}
                    {/* Needs Review Ring overlay */}
                    {needsReviewPct > 0 && (
                      <circle
                        cx="18"
                        cy="18"
                        r="14.5"
                        fill="none"
                        stroke="#FCD3D7"
                        strokeWidth="4.5"
                        strokeDasharray={`${needsReviewPct} 100`}
                        strokeDashoffset={`-${strongPct + partialPct}`}
                      />
                    )}
                  </svg>
                  {/* Center Text inside Donut Hole */}
                  <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                    <span style={{ fontSize: "1.35rem", fontWeight: "800", color: "#102A43", lineHeight: "1" }}>{totalQ}</span>
                    <span style={{ fontSize: "0.65rem", fontWeight: "600", color: "#5E7187" }}>Questions</span>
                  </div>
                </div>

                {/* Legend List */}
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.55rem" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.8125rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                      <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#3D9468" }} />
                      <span style={{ color: "#5E7187" }}>Strong (≥70%)</span>
                    </div>
                    <div style={{ display: "flex", gap: "0.75rem", fontWeight: "700", color: "#102A43" }}>
                      <span>{strongCount}</span>
                      <span style={{ color: "#829AB1", width: "32px", textAlign: "right" }}>{strongPct}%</span>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.8125rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                      <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#C58A27" }} />
                      <span style={{ color: "#5E7187" }}>Partial (40–69%)</span>
                    </div>
                    <div style={{ display: "flex", gap: "0.75rem", fontWeight: "700", color: "#102A43" }}>
                      <span>{partialCount}</span>
                      <span style={{ color: "#829AB1", width: "32px", textAlign: "right" }}>{partialPct}%</span>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.8125rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                      <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#D35D5D" }} />
                      <span style={{ color: "#5E7187" }}>Needs Review (&lt;40%)</span>
                    </div>
                    <div style={{ display: "flex", gap: "0.75rem", fontWeight: "700", color: "#102A43" }}>
                      <span>{needsReviewCount}</span>
                      <span style={{ color: "#829AB1", width: "32px", textAlign: "right" }}>{needsReviewPct}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 2. KEY TAKEAWAYS (Exact match to Reference 2 right card) */}
            <div className="card-white" style={{ padding: "1.5rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "1rem" }}>
                <span style={{ fontSize: "1.25rem" }}>💡</span>
                <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#102A43", margin: 0 }}>
                  Key Takeaways
                </h2>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                {/* What You Did Well Box */}
                <div style={{ background: "#EAF7F0", border: "1px solid #C6ECD5", borderRadius: "12px", padding: "1rem 1.15rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "#3D9468", fontWeight: "700", fontSize: "0.875rem", marginBottom: "0.5rem" }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    What You Did Well
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                    {strengths && strengths.length > 0 ? (
                      strengths.map((s, idx) => (
                        <div key={idx} style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.8125rem", color: "#102A43", lineHeight: "1.4" }}>
                          <span style={{ color: "#3D9468", fontWeight: "700" }}>✓</span>
                          <span>{s}</span>
                        </div>
                      ))
                    ) : (
                      <>
                        <div style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.8125rem", color: "#102A43", lineHeight: "1.4" }}>
                          <span style={{ color: "#3D9468", fontWeight: "700" }}>✓</span>
                          <span>Maintained strong communication delivery in multiple responses.</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.8125rem", color: "#102A43", lineHeight: "1.4" }}>
                          <span style={{ color: "#3D9468", fontWeight: "700" }}>✓</span>
                          <span>Attempted all {total_questions_answered} questions in the interview session.</span>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* Areas for Improvement Box */}
                <div style={{ background: "#FDEEEF", border: "1px solid #FCD3D7", borderRadius: "12px", padding: "1rem 1.15rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "#D35D5D", fontWeight: "700", fontSize: "0.875rem", marginBottom: "0.5rem" }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                    Areas for Improvement
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                    {weaknesses && weaknesses.length > 0 ? (
                      weaknesses.map((w, idx) => (
                        <div key={idx} style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.8125rem", color: "#102A43", lineHeight: "1.4" }}>
                          <span style={{ color: "#D35D5D", fontWeight: "700" }}>!</span>
                          <span>{w}</span>
                        </div>
                      ))
                    ) : (
                      <>
                        <div style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.8125rem", color: "#102A43", lineHeight: "1.4" }}>
                          <span style={{ color: "#D35D5D", fontWeight: "700" }}>!</span>
                          <span>Technical understanding needs significant improvement ({overall_technical_score.toFixed(1)}% overall).</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.8125rem", color: "#102A43", lineHeight: "1.4" }}>
                          <span style={{ color: "#D35D5D", fontWeight: "700" }}>!</span>
                          <span>{needsReviewCount} response{needsReviewCount !== 1 ? "s" : ""} require review.</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.8125rem", color: "#102A43", lineHeight: "1.4" }}>
                          <span style={{ color: "#D35D5D", fontWeight: "700" }}>!</span>
                          <span>Focus on the concepts covered in {weakQText}.</span>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* 3. NEXT STEPS (Exact match to Reference 2 numbered list) */}
            <div className="card-white" style={{ padding: "1.5rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "1rem" }}>
                <span style={{ fontSize: "1.25rem" }}>📑</span>
                <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#102A43", margin: 0 }}>
                  Next Steps
                </h2>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                {next_steps && next_steps.length > 0 ? (
                  next_steps.map((step, idx) => (
                    <div key={idx} style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem" }}>
                      <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: "#2F66C5", color: "#FFFFFF", fontSize: "0.75rem", fontWeight: "700", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        {idx + 1}
                      </div>
                      <div style={{ color: "#102A43", fontSize: "0.8125rem", lineHeight: "1.4", paddingTop: "0.15rem" }}>
                        {step}
                      </div>
                    </div>
                  ))
                ) : (
                  <>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem" }}>
                      <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: "#2F66C5", color: "#FFFFFF", fontSize: "0.75rem", fontWeight: "700", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        1
                      </div>
                      <div style={{ color: "#102A43", fontSize: "0.8125rem", lineHeight: "1.4", paddingTop: "0.15rem" }}>
                        Review the concepts behind your lowest-scoring questions and retry this topic.
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem" }}>
                      <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: "#2F66C5", color: "#FFFFFF", fontSize: "0.75rem", fontWeight: "700", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        2
                      </div>
                      <div style={{ color: "#102A43", fontSize: "0.8125rem", lineHeight: "1.4", paddingTop: "0.15rem" }}>
                        Practice concise, structured verbal explanations.
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem" }}>
                      <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: "#2F66C5", color: "#FFFFFF", fontSize: "0.75rem", fontWeight: "700", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        3
                      </div>
                      <div style={{ color: "#102A43", fontSize: "0.8125rem", lineHeight: "1.4", paddingTop: "0.15rem" }}>
                        Prioritize the concepts represented by {weakQText}.
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>

          </div>

        </div>
      </main>
    </div>
  );
}

export default function AssessmentReportPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: "center", padding: "4rem", color: "#5E7187" }}>Loading report dashboard...</div>}>
      <AssessmentReportContent />
    </Suspense>
  );
}

