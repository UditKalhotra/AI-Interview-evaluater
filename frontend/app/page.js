"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "./components/Navbar";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const router = useRouter();
  const [status, setStatus] = useState("checking");
  const [health, setHealth] = useState(null);
  const [candidateName, setCandidateName] = useState("");
  const [isStarting, setIsStarting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [showConfig, setShowConfig] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => {
        if (!res.ok) throw new Error(`Backend status ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setHealth(data);
        setStatus("connected");
      })
      .catch(() => setStatus("error"));
  }, []);

  const handleStartInterview = async () => {
    try {
      setIsStarting(true);
      setErrorMessage(null);
      const res = await fetch(`${API_URL}/interview/session/start`, {
        method: "POST",
      });

      if (!res.ok) {
        throw new Error(`Failed to initialize session (status ${res.status})`);
      }

      const data = await res.json();
      const sessionId = data.session_id;
      router.push(`/interview?session_id=${encodeURIComponent(sessionId)}${candidateName ? `&candidate=${encodeURIComponent(candidateName)}` : ""}`);
    } catch (err) {
      setIsStarting(false);
      setErrorMessage(err.message || "Failed to start interview session");
    }
  };

  const scrollToSection = (id) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Navbar />

      <main style={{ flex: 1 }}>
        {/* HERO SECTION */}
        <section style={styles.heroSection}>
          <div style={styles.heroContainer}>
            <div style={styles.heroBadge}>
              <span>Structured AI Assessment Engine</span>
            </div>

            <h1 style={styles.heroTitle}>
              Professional AI Technical <br />
              <span style={styles.titleGradient}>Interview & Evaluation Platform</span>
            </h1>

            <p style={styles.heroSubtitle}>
              Assess engineering talent with clarity. Candidates receive text-based technical questions with structured preparation time, speak their solutions naturally, and receive comprehensive IRT-calibrated & behavioral analytics.
            </p>

            <div style={styles.heroCtas}>
              <button
                style={styles.primaryCta}
                onClick={() => {
                  setShowConfig(true);
                  scrollToSection("prepare-section");
                }}
              >
                Prepare & Start Assessment &rarr;
              </button>
              <button
                style={styles.secondaryCta}
                onClick={() => scrollToSection("how-it-works")}
              >
                Learn How It Works
              </button>
            </div>
          </div>
        </section>

        {/* PILLARS / HIGHLIGHTS BAR */}
        <section style={styles.pillarsSection}>
          <div style={styles.pillarsContainer}>
            <div style={styles.pillarCard}>
              <div style={styles.pillarIcon}>📝</div>
              <h3 style={styles.pillarTitle}>Text Question Display</h3>
              <p style={styles.pillarText}>
                No voice audio distractions. Questions are presented clearly as text on screen with 1 minute of preparation time.
              </p>
            </div>

            <div style={styles.pillarCard}>
              <div style={styles.pillarIcon}>⏱️</div>
              <h3 style={styles.pillarTitle}>Repeat & Review</h3>
              <p style={styles.pillarText}>
                Candidates can click "Repeat Question" anytime to re-display and re-read the question statement with full focus.
              </p>
            </div>

            <div style={styles.pillarCard}>
              <div style={styles.pillarIcon}>🎯</div>
              <h3 style={styles.pillarTitle}>Adaptive IRT Engine</h3>
              <p style={styles.pillarText}>
                Questions automatically adjust in difficulty based on candidate response history using Item Response Theory.
              </p>
            </div>

            <div style={styles.pillarCard}>
              <div style={styles.pillarIcon}>📊</div>
              <h3 style={styles.pillarTitle}>Comprehensive Analytics</h3>
              <p style={styles.pillarText}>
                Dual evaluation combining LSA technical correctness and Gemini behavioral delivery analysis.
              </p>
            </div>
          </div>
        </section>

        {/* HOW IT WORKS SECTION */}
        <section id="how-it-works" style={styles.howSection}>
          <div style={styles.sectionContainer}>
            <div style={styles.sectionHeader}>
              <span style={styles.sectionTag}>Structured Workflow</span>
              <h2 style={styles.sectionTitle}>How the Assessment Works</h2>
              <p style={styles.sectionSubtitle}>
                Four simple steps designed to provide a fair, transparent, and professional candidate experience.
              </p>
            </div>

            <div style={styles.stepsGrid}>
              {/* Step 1 */}
              <div style={styles.stepCard}>
                <div style={styles.stepNumber}>01</div>
                <h3 style={styles.stepTitle}>Session Initialization</h3>
                <p style={styles.stepDesc}>
                  The system boots an isolated candidate session and initializes the Item Response Theory (IRT) baseline.
                </p>
              </div>

              {/* Step 2 */}
              <div style={styles.stepCard}>
                <div style={styles.stepNumber}>02</div>
                <h3 style={styles.stepTitle}>Read Question (1 Min Prep)</h3>
                <p style={styles.stepDesc}>
                  The question text appears on screen. Take up to 1 minute to read, understand, and outline your spoken response. Click "Repeat Question" if needed.
                </p>
              </div>

              {/* Step 3 */}
              <div style={styles.stepCard}>
                <div style={styles.stepNumber}>03</div>
                <h3 style={styles.stepTitle}>Spoken Response</h3>
                <p style={styles.stepDesc}>
                  Click "Start Answering" when ready and speak your solution clearly into your microphone within the allotted time limit.
                </p>
              </div>

              {/* Step 4 */}
              <div style={styles.stepCard}>
                <div style={styles.stepNumber}>04</div>
                <h3 style={styles.stepTitle}>AI Scoring & Report</h3>
                <p style={styles.stepDesc}>
                  Answers are transcribed, evaluated for semantic technical accuracy (LSA) and communication clarity (Gemini), generating an instant diagnostic report.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* PREPARE & CONFIGURE SECTION */}
        <section id="prepare-section" style={styles.prepareSection}>
          <div style={styles.sectionContainer}>
            <div style={styles.prepareCard}>
              <div style={styles.prepareHeader}>
                <h2>Assessment Preparation & Launch</h2>
                <p>Review candidate guidelines and confirm your setup before entering the assessment room.</p>
              </div>

              <div style={styles.guidelinesGrid}>
                <div style={styles.guidelineItem}>
                  <span style={styles.checkIcon}>✓</span>
                  <div>
                    <strong>Quiet Environment</strong>
                    <p>Ensure you are in a quiet area free from background noise for clear voice transcription.</p>
                  </div>
                </div>

                <div style={styles.guidelineItem}>
                  <span style={styles.checkIcon}>✓</span>
                  <div>
                    <strong>Microphone Access</strong>
                    <p>Grant browser permissions for your microphone when prompted upon starting.</p>
                  </div>
                </div>

                <div style={styles.guidelineItem}>
                  <span style={styles.checkIcon}>✓</span>
                  <div>
                    <strong>Question Structure</strong>
                    <p>Each question displays on screen with a 1-minute prep timer before recording starts.</p>
                  </div>
                </div>

                <div style={styles.guidelineItem}>
                  <span style={styles.checkIcon}>✓</span>
                  <div>
                    <strong>5 Questions (~12 Mins)</strong>
                    <p>The assessment consists of 5 adaptive questions tailored to your skill level.</p>
                  </div>
                </div>
              </div>

              {/* Form Input */}
              <div style={styles.configForm}>
                <div style={styles.inputGroup}>
                  <label style={styles.label}>Candidate Name or ID (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. Jane Doe"
                    value={candidateName}
                    onChange={(e) => setCandidateName(e.target.value)}
                    style={styles.input}
                  />
                </div>

                {errorMessage && (
                  <div style={styles.errorBanner}>
                    ⚠️ {errorMessage}
                  </div>
                )}

                <button
                  onClick={handleStartInterview}
                  disabled={status !== "connected" || isStarting}
                  style={{
                    ...styles.startBtn,
                    opacity: status === "connected" && !isStarting ? 1 : 0.6,
                    cursor: status === "connected" && !isStarting ? "pointer" : "not-allowed",
                  }}
                >
                  {isStarting ? (
                    <>⏳ Initializing Assessment Session...</>
                  ) : (
                    <>🚀 Begin Technical Interview Session &rarr;</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer style={styles.footer}>
        <div style={styles.footerContainer}>
          <div>
            <div style={styles.footerBrand}>TalentEval AI</div>
            <div style={styles.footerSub}>Enterprise Technical Assessment & Candidate Evaluation Platform</div>
          </div>
          <div style={styles.footerRights}>
            © {new Date().getFullYear()} TalentEval AI. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

const styles = {
  heroSection: {
    padding: "5rem 1.5rem 4rem 1.5rem",
    background: "linear-gradient(180deg, #0b0f19 0%, #111827 100%)",
    textAlign: "center",
  },
  heroContainer: {
    maxWidth: "850px",
    margin: "0 auto",
  },
  heroBadge: {
    display: "inline-block",
    padding: "0.4rem 1rem",
    borderRadius: "9999px",
    background: "rgba(37, 99, 235, 0.12)",
    border: "1px solid rgba(37, 99, 235, 0.3)",
    color: "#60a5fa",
    fontSize: "0.85rem",
    fontWeight: "600",
    marginBottom: "1.5rem",
  },
  heroTitle: {
    fontSize: "clamp(2.25rem, 5vw, 3.5rem)",
    fontWeight: "800",
    lineHeight: "1.15",
    color: "#f8fafc",
    marginBottom: "1.25rem",
    letterSpacing: "-0.02em",
  },
  titleGradient: {
    background: "linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
  },
  heroSubtitle: {
    fontSize: "1.15rem",
    color: "#94a3b8",
    lineHeight: "1.6",
    marginBottom: "2.5rem",
    maxWidth: "720px",
    margin: "0 auto 2.5rem auto",
  },
  heroCtas: {
    display: "flex",
    gap: "1rem",
    justifyContent: "center",
    flexWrap: "wrap",
  },
  primaryCta: {
    padding: "0.9rem 2rem",
    fontSize: "1.05rem",
    fontWeight: "700",
    borderRadius: "10px",
    background: "#2563eb",
    color: "#ffffff",
    border: "none",
    cursor: "pointer",
    boxShadow: "0 10px 25px rgba(37, 99, 235, 0.3)",
    transition: "transform 0.15s ease",
  },
  secondaryCta: {
    padding: "0.9rem 1.75rem",
    fontSize: "1.05rem",
    fontWeight: "600",
    borderRadius: "10px",
    background: "#151d2a",
    color: "#cbd5e1",
    border: "1px solid #233044",
    cursor: "pointer",
  },
  pillarsSection: {
    padding: "3rem 1.5rem",
    background: "#111827",
    borderTop: "1px solid #1f2937",
    borderBottom: "1px solid #1f2937",
  },
  pillarsContainer: {
    maxWidth: "1200px",
    margin: "0 auto",
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: "1.5rem",
  },
  pillarCard: {
    background: "#151d2a",
    padding: "1.5rem",
    borderRadius: "12px",
    border: "1px solid #233044",
  },
  pillarIcon: {
    fontSize: "1.75rem",
    marginBottom: "0.75rem",
  },
  pillarTitle: {
    fontSize: "1.1rem",
    fontWeight: "700",
    color: "#f8fafc",
    marginBottom: "0.5rem",
  },
  pillarText: {
    fontSize: "0.875rem",
    color: "#94a3b8",
    lineHeight: "1.5",
  },
  howSection: {
    padding: "5rem 1.5rem",
    background: "#0b0f19",
  },
  sectionContainer: {
    maxWidth: "1100px",
    margin: "0 auto",
  },
  sectionHeader: {
    textAlign: "center",
    marginBottom: "3.5rem",
  },
  sectionTag: {
    color: "#3b82f6",
    fontSize: "0.85rem",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  sectionTitle: {
    fontSize: "2.25rem",
    fontWeight: "800",
    color: "#f8fafc",
    marginTop: "0.5rem",
    marginBottom: "0.75rem",
  },
  sectionSubtitle: {
    color: "#94a3b8",
    fontSize: "1.05rem",
  },
  stepsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: "1.5rem",
  },
  stepCard: {
    background: "#151d2a",
    border: "1px solid #233044",
    borderRadius: "14px",
    padding: "1.75rem",
    position: "relative",
  },
  stepNumber: {
    fontSize: "2.5rem",
    fontWeight: "900",
    color: "#233044",
    lineHeight: "1",
    marginBottom: "1rem",
  },
  stepTitle: {
    fontSize: "1.15rem",
    fontWeight: "700",
    color: "#f8fafc",
    marginBottom: "0.5rem",
  },
  stepDesc: {
    fontSize: "0.9rem",
    color: "#94a3b8",
    lineHeight: "1.5",
  },
  prepareSection: {
    padding: "4rem 1.5rem 6rem 1.5rem",
    background: "#111827",
    borderTop: "1px solid #1f2937",
  },
  prepareCard: {
    background: "#151d2a",
    border: "1px solid #233044",
    borderRadius: "16px",
    padding: "2.5rem",
    maxWidth: "800px",
    margin: "0 auto",
  },
  prepareHeader: {
    marginBottom: "2rem",
    textAlign: "center",
  },
  guidelinesGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
    gap: "1.25rem",
    marginBottom: "2.5rem",
  },
  guidelineItem: {
    display: "flex",
    gap: "0.85rem",
    alignItems: "flex-start",
    background: "#0f1724",
    padding: "1rem 1.25rem",
    borderRadius: "10px",
    border: "1px solid #233044",
  },
  checkIcon: {
    color: "#10b981",
    fontWeight: "900",
    fontSize: "1.1rem",
  },
  configForm: {
    borderTop: "1px solid #233044",
    paddingTop: "2rem",
    display: "flex",
    flexDirection: "column",
    gap: "1.25rem",
  },
  inputGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
  },
  label: {
    fontSize: "0.875rem",
    fontWeight: "600",
    color: "#cbd5e1",
  },
  input: {
    padding: "0.75rem 1rem",
    borderRadius: "8px",
    background: "#0f1724",
    border: "1px solid #233044",
    color: "#f8fafc",
    fontSize: "0.95rem",
    outline: "none",
  },
  errorBanner: {
    padding: "0.75rem 1rem",
    background: "rgba(239, 68, 68, 0.12)",
    border: "1px solid rgba(239, 68, 68, 0.3)",
    color: "#fca5a5",
    borderRadius: "8px",
    fontSize: "0.9rem",
  },
  startBtn: {
    padding: "1rem 2rem",
    fontSize: "1.1rem",
    fontWeight: "700",
    borderRadius: "10px",
    background: "linear-gradient(135deg, #2563eb 0%, #4f46e5 100%)",
    color: "#ffffff",
    border: "none",
    boxShadow: "0 10px 25px rgba(37, 99, 235, 0.3)",
    transition: "all 0.2s ease",
  },
  footer: {
    background: "#0b0f19",
    borderTop: "1px solid #1f2937",
    padding: "2rem 1.5rem",
  },
  footerContainer: {
    maxWidth: "1200px",
    margin: "0 auto",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "1rem",
  },
  footerBrand: {
    fontWeight: "700",
    color: "#f8fafc",
    fontSize: "1rem",
  },
  footerSub: {
    color: "#64748b",
    fontSize: "0.8rem",
  },
  footerRights: {
    color: "#64748b",
    fontSize: "0.8rem",
  },
};
