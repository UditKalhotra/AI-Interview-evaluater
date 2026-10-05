"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "./components/Navbar";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const router = useRouter();
  const [status, setStatus] = useState("checking");
  const [topics, setTopics] = useState([]);
  const [loadingTopics, setLoadingTopics] = useState(true);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [candidateName, setCandidateName] = useState("");
  const [isStarting, setIsStarting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => {
        if (!res.ok) throw new Error(`Backend status ${res.status}`);
        return res.json();
      })
      .then(() => {
        setStatus("connected");
      })
      .catch(() => setStatus("error"));

    fetch(`${API_URL}/questions/topics`)
      .then((res) => {
        if (!res.ok) throw new Error("Could not fetch topics");
        return res.json();
      })
      .then((data) => {
        setTopics(data || []);
        if (data && data.length > 0) {
          setSelectedTopic(data[0].topic);
        }
        setLoadingTopics(false);
      })
      .catch((err) => {
        console.error("Failed to load topics:", err);
        setLoadingTopics(false);
      });
  }, []);

  const handleStartInterview = async () => {
    if (!selectedTopic) {
      setErrorMessage("Please select a topic to begin.");
      return;
    }

    try {
      setIsStarting(true);
      setErrorMessage(null);
      const formData = new FormData();
      formData.append("topic", selectedTopic);

      const res = await fetch(`${API_URL}/interview/session/start`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Failed to initialize session (status ${res.status})`);
      }

      const data = await res.json();
      const sessionId = data.session_id;
      router.push(
        `/interview?session_id=${encodeURIComponent(sessionId)}&topic=${encodeURIComponent(
          selectedTopic
        )}${candidateName ? `&candidate=${encodeURIComponent(candidateName)}` : ""}`
      );
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
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", color: "#0F2742" }}>
      <Navbar />

      <main style={{ flex: 1 }}>
        {/* HERO SECTION - TWO COLUMN MATCHING REFERENCE 1 */}
        <section style={styles.heroSection}>
          <div style={styles.heroContainer}>
            {/* Left Column: Text & CTAs */}
            <div style={styles.heroLeft}>
              <div style={styles.eyebrowLabel}>
                PRACTICE · ASSESS · IMPROVE
              </div>

              <h1 style={styles.heroTitle}>
                Voice-Based Technical <br />
                Assessment Platform
              </h1>

              <p style={styles.heroSubtitle}>
                Evaluate your technical knowledge and communication skills through structured, topic-driven interviews with real-time analysis and detailed feedback.
              </p>

              <div style={styles.heroCtas}>
                <button
                  style={styles.primaryCta}
                  onClick={() => scrollToSection("topic-selection")}
                >
                  Start Assessment →
                </button>
                <button
                  style={styles.secondaryCta}
                  onClick={() => scrollToSection("how-it-works")}
                >
                  <span style={styles.playIcon}>▶</span> See How It Works
                </button>
              </div>

              {/* 3 Compact Feature Highlights */}
              <div style={styles.compactFeaturesRow}>
                <div style={styles.compactFeatureItem}>
                  <div style={{ ...styles.compactIconBox, background: "#EAF2FF", color: "#2F66C5" }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>
                  </div>
                  <div>
                    <div style={styles.compactTitle}>Voice-Based Evaluation</div>
                    <div style={styles.compactSub}>Natural speaking interface</div>
                  </div>
                </div>

                <div style={styles.compactFeatureItem}>
                  <div style={{ ...styles.compactIconBox, background: "#EAF7F0", color: "#3D9468" }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                  </div>
                  <div>
                    <div style={styles.compactTitle}>Topic-Driven Question Bank</div>
                    <div style={styles.compactSub}>Multiple difficulty levels</div>
                  </div>
                </div>

                <div style={styles.compactFeatureItem}>
                  <div style={{ ...styles.compactIconBox, background: "#EAF2FF", color: "#2F66C5" }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>
                  </div>
                  <div>
                    <div style={styles.compactTitle}>Detailed Performance Report</div>
                    <div style={styles.compactSub}>Actionable feedback</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Interactive Mockup Product Preview */}
            <div style={styles.heroRight}>
              <div style={styles.mockupContainer}>
                {/* Browser Window Header */}
                <div style={styles.mockupWindowHeader}>
                  <div style={styles.windowDots}>
                    <span style={{ background: "#FF5F56", width: "10px", height: "10px", borderRadius: "50%" }} />
                    <span style={{ background: "#FFBD2E", width: "10px", height: "10px", borderRadius: "50%" }} />
                    <span style={{ background: "#27C93F", width: "10px", height: "10px", borderRadius: "50%" }} />
                  </div>
                  <div style={styles.windowTitle}>
                    <span style={{ fontWeight: "800", color: "#2F66C5" }}>TE</span> TalentEval
                  </div>
                  <div style={styles.userAvatar}>👤</div>
                </div>

                {/* Inner Mockup Body */}
                <div style={styles.mockupBody}>
                  {/* Left Mockup Sidebar */}
                  <div style={styles.mockupSidebar}>
                    <div style={{ ...styles.sidebarItem, background: "#EAF2FF", color: "#2F66C5", fontWeight: "700" }}>
                      📊 Dashboard
                    </div>
                    <div style={styles.sidebarItem}>📋 Assessment</div>
                    <div style={styles.sidebarItem}>📚 Topics</div>
                    <div style={styles.sidebarItem}>📈 Results</div>
                    <div style={styles.sidebarItem}>👤 Profile</div>
                  </div>

                  {/* Right Mockup Content Area */}
                  <div style={styles.mockupContent}>
                    <div style={styles.mockupHeaderRow}>
                      <span style={{ fontWeight: "700", color: "#102A43", fontSize: "0.95rem" }}>Assessment in Progress</span>
                    </div>

                    <div style={styles.mockupMetaRow}>
                      <span style={{ color: "#5E7187", fontWeight: "600", fontSize: "0.85rem" }}>Q3 / 6</span>
                      <span style={styles.mockupTopicTag}>Sorting and Algorithms</span>
                      <span style={styles.mockupDiffTag}>Medium</span>
                      <span style={styles.mockupTimer}>⏱️ 02:15</span>
                    </div>

                    {/* Question Card Inside Mockup */}
                    <div style={styles.mockupQuestionCard}>
                      <div style={styles.mockupQuestionStatement}>
                        Explain the main idea behind selection sort.
                      </div>

                      {/* Animated Audio Waveform Area */}
                      <div style={styles.waveformBox}>
                        <div style={styles.waveformContainer}>
                          <span className="animate-wave-1" style={styles.waveBar} />
                          <span className="animate-wave-2" style={styles.waveBar} />
                          <span className="animate-wave-3" style={styles.waveBar} />
                          <span className="animate-wave-4" style={styles.waveBar} />
                          <span className="animate-wave-5" style={styles.waveBar} />
                          <span className="animate-wave-2" style={styles.waveBar} />
                          <span className="animate-wave-1" style={styles.waveBar} />
                        </div>
                        <button style={styles.mockupRecordBtn}>⏹</button>
                      </div>
                      <div style={styles.listeningText}>Listening...</div>
                    </div>

                    {/* Live Audio Metrics Row */}
                    <div style={styles.mockupMetricsGrid}>
                      <div style={styles.mockupMetricBox}>
                        <div style={{ ...styles.mockupMetricIcon, background: "#EAF7F0", color: "#3D9468" }}>📊</div>
                        <div>
                          <div style={styles.mockupMetricLabel}>Speaking Rate</div>
                          <div style={styles.mockupMetricVal}>118 <span style={{ fontSize: "0.75rem", color: "#3D9468" }}>WPM</span></div>
                        </div>
                      </div>

                      <div style={styles.mockupMetricBox}>
                        <div style={{ ...styles.mockupMetricIcon, background: "#FFF7DF", color: "#C58A27" }}>⏸</div>
                        <div>
                          <div style={styles.mockupMetricLabel}>Pause Count</div>
                          <div style={styles.mockupMetricVal}>2</div>
                        </div>
                      </div>

                      <div style={styles.mockupMetricBox}>
                        <div style={{ ...styles.mockupMetricIcon, background: "#FDEEEF", color: "#D35D5D" }}>📉</div>
                        <div>
                          <div style={styles.mockupMetricLabel}>Fillers Detected</div>
                          <div style={styles.mockupMetricVal}>1</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* FEATURE STRIP - 4 HORIZONTAL CARDS MATCHING REFERENCE 1 */}
        <section style={styles.featureStripSection}>
          <div style={styles.sectionContainer}>
            <div style={styles.featureStripGrid}>
              <div style={styles.featureStripCard}>
                <div style={{ ...styles.featureIconContainer, background: "#EAF2FF", color: "#2F66C5" }}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>
                </div>
                <h3 style={styles.featureStripTitle}>Real Interview Experience</h3>
                <p style={styles.featureStripDesc}>
                  Answer questions by speaking naturally, just like in a real interview.
                </p>
              </div>

              <div style={styles.featureStripCard}>
                <div style={{ ...styles.featureIconContainer, background: "#EAF7F0", color: "#3D9468" }}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                </div>
                <h3 style={styles.featureStripTitle}>Comprehensive Evaluation</h3>
                <p style={styles.featureStripDesc}>
                  Assesses both technical accuracy and communication skills.
                </p>
              </div>

              <div style={styles.featureStripCard}>
                <div style={{ ...styles.featureIconContainer, background: "#FFF7DF", color: "#C58A27" }}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                </div>
                <h3 style={styles.featureStripTitle}>Multiple Topics</h3>
                <p style={styles.featureStripDesc}>
                  Covers key computer science topics with varying difficulty levels.
                </p>
              </div>

              <div style={styles.featureStripCard}>
                <div style={{ ...styles.featureIconContainer, background: "#FDEEEF", color: "#D35D5D" }}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                </div>
                <h3 style={styles.featureStripTitle}>Detailed Feedback</h3>
                <p style={styles.featureStripDesc}>
                  Get a comprehensive report with strengths, weak areas, and next steps.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* TOPIC SELECTION SECTION */}
        <section id="topic-selection" style={styles.topicsSection}>
          <div style={styles.sectionContainer}>
            <div style={styles.sectionHeader}>
              <span style={styles.sectionTag}>Select Assessment Domain</span>
              <h2 style={styles.sectionTitle}>Available Technical Topics</h2>
              <p style={styles.sectionSubtitle}>
                Select an active topic below to load its dedicated question bank.
              </p>
            </div>

            {loadingTopics ? (
              <div style={{ textAlign: "center", padding: "3rem", color: "#5E7187" }}>
                Loading available topics...
              </div>
            ) : topics.length === 0 ? (
              <div style={{ textAlign: "center", padding: "3rem", color: "#D35D5D" }}>
                No active question topics found in database.
              </div>
            ) : (
              <div style={styles.topicsGrid}>
                {topics.map((t) => {
                  const isSelected = selectedTopic === t.topic;
                  return (
                    <div
                      key={t.topic}
                      onClick={() => setSelectedTopic(t.topic)}
                      style={{
                        ...styles.topicCard,
                        ...(isSelected ? styles.topicCardSelected : {}),
                      }}
                    >
                      <div style={styles.topicHeaderRow}>
                        <h3 style={styles.topicCardTitle}>{t.topic}</h3>
                        <span style={styles.questionCountBadge}>
                          {t.question_count} Question{t.question_count > 1 ? "s" : ""}
                        </span>
                      </div>
                      <p style={styles.topicCardDesc}>
                        Complete all {t.question_count} active question{t.question_count > 1 ? "s" : ""} for {t.topic}.
                      </p>
                      <div style={{ ...styles.selectIndicator, color: isSelected ? "#2F66C5" : "#5E7187" }}>
                        {isSelected ? "✓ Selected Topic" : "Click to Select"}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* PREPARE & START FORM */}
            <div style={styles.prepareCard}>
              <div style={styles.prepareHeader}>
                <h3 style={{ fontSize: "1.15rem", fontWeight: "800", color: "#102A43", marginBottom: "0.35rem" }}>Candidate Setup & Launch</h3>
                <p style={{ fontSize: "0.9rem", color: "#5E7187" }}>Selected Topic: <strong style={{ color: "#2F66C5" }}>{selectedTopic || "None"}</strong></p>
              </div>

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
                    {errorMessage}
                  </div>
                )}

                <button
                  onClick={handleStartInterview}
                  disabled={status !== "connected" || isStarting || !selectedTopic}
                  style={{
                    ...styles.startBtn,
                    opacity: status === "connected" && !isStarting && selectedTopic ? 1 : 0.6,
                    cursor: status === "connected" && !isStarting && selectedTopic ? "pointer" : "not-allowed",
                  }}
                >
                  {isStarting ? "Initializing Assessment Session..." : `Start Assessment →`}
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* HOW IT WORKS SECTION - MATCHING REFERENCE 1 */}
        <section id="how-it-works" style={styles.howSection}>
          <div style={styles.sectionContainer}>
            <div style={styles.sectionHeader}>
              <span style={styles.sectionTag}>SIMPLE PROCESS</span>
              <h2 style={styles.sectionTitle}>How It Works</h2>
              <p style={styles.sectionSubtitle}>
                Get your detailed assessment report in just a few steps.
              </p>
            </div>

            <div style={styles.stepsGrid}>
              <div style={styles.stepCard}>
                <div style={styles.stepHeader}>
                  <div style={styles.stepBadgeNum}>1</div>
                  <div style={{ ...styles.stepIconBox, background: "#EAF2FF", color: "#2F66C5" }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
                  </div>
                </div>
                <h3 style={styles.stepTitle}>Select a Topic</h3>
                <p style={styles.stepDesc}>
                  Choose from a variety of technical topics and difficulty levels.
                </p>
              </div>

              <div style={styles.stepCard}>
                <div style={styles.stepHeader}>
                  <div style={styles.stepBadgeNum}>2</div>
                  <div style={{ ...styles.stepIconBox, background: "#EAF7F0", color: "#3D9468" }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>
                  </div>
                </div>
                <h3 style={styles.stepTitle}>Take the Assessment</h3>
                <p style={styles.stepDesc}>
                  Answer 6 structured questions using your voice.
                </p>
              </div>

              <div style={styles.stepCard}>
                <div style={styles.stepHeader}>
                  <div style={styles.stepBadgeNum}>3</div>
                  <div style={{ ...styles.stepIconBox, background: "#FFF7DF", color: "#C58A27" }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                  </div>
                </div>
                <h3 style={styles.stepTitle}>Automatic Evaluation</h3>
                <p style={styles.stepDesc}>
                  Your responses are analyzed for technical content and delivery.
                </p>
              </div>

              <div style={styles.stepCard}>
                <div style={styles.stepHeader}>
                  <div style={styles.stepBadgeNum}>4</div>
                  <div style={{ ...styles.stepIconBox, background: "#FDEEEF", color: "#D35D5D" }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                  </div>
                </div>
                <h3 style={styles.stepTitle}>Get Detailed Results</h3>
                <p style={styles.stepDesc}>
                  View your performance with personalized feedback and recommendations.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer style={styles.footer}>
        <div style={styles.footerContainer}>
          <div>
            <div style={styles.footerBrand}>TalentEval</div>
            <div style={styles.footerSub}>Technical Assessment Platform</div>
          </div>
          <div style={styles.footerRights}>
            © {new Date().getFullYear()} TalentEval. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

const styles = {
  heroSection: {
    padding: "3.5rem 1.5rem 4rem 1.5rem",
    background: "transparent",
  },
  heroContainer: {
    maxWidth: "1240px",
    margin: "0 auto",
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(450px, 1fr))",
    gap: "3rem",
    alignItems: "center",
  },
  heroLeft: {
    display: "flex",
    flexDirection: "column",
    gap: "1.25rem",
  },
  eyebrowLabel: {
    fontSize: "0.75rem",
    fontWeight: "700",
    letterSpacing: "0.08em",
    color: "#5E7187",
    textTransform: "uppercase",
  },
  heroTitle: {
    fontSize: "clamp(2.25rem, 3.5vw, 3rem)",
    fontWeight: "900",
    lineHeight: "1.15",
    color: "#102A43",
    letterSpacing: "-0.025em",
  },
  heroSubtitle: {
    fontSize: "1.05rem",
    color: "#5E7187",
    lineHeight: "1.6",
    maxWidth: "540px",
  },
  heroCtas: {
    display: "flex",
    gap: "1rem",
    alignItems: "center",
    marginTop: "0.5rem",
    flexWrap: "wrap",
  },
  primaryCta: {
    padding: "0.85rem 1.75rem",
    fontSize: "0.95rem",
    fontWeight: "700",
    borderRadius: "10px",
    background: "#2F66C5",
    color: "#ffffff",
    border: "none",
    cursor: "pointer",
    boxShadow: "0 4px 15px rgba(47, 102, 197, 0.3)",
  },
  secondaryCta: {
    padding: "0.85rem 1.5rem",
    fontSize: "0.95rem",
    fontWeight: "600",
    borderRadius: "10px",
    background: "#FFFFFF",
    color: "#102A43",
    border: "1px solid #E2E7EF",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    boxShadow: "0 2px 8px rgba(30, 60, 90, 0.04)",
  },
  playIcon: {
    color: "#2F66C5",
    fontSize: "0.8rem",
  },
  compactFeaturesRow: {
    display: "flex",
    gap: "1.25rem",
    marginTop: "1.5rem",
    flexWrap: "wrap",
  },
  compactFeatureItem: {
    display: "flex",
    alignItems: "center",
    gap: "0.6rem",
  },
  compactIconBox: {
    width: "36px",
    height: "36px",
    borderRadius: "10px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  compactTitle: {
    fontSize: "0.8125rem",
    fontWeight: "700",
    color: "#102A43",
    lineHeight: "1.2",
  },
  compactSub: {
    fontSize: "0.725rem",
    color: "#5E7187",
  },
  heroRight: {
    display: "flex",
    justifyContent: "center",
  },
  mockupContainer: {
    width: "100%",
    maxWidth: "560px",
    background: "#FFFFFF",
    borderRadius: "18px",
    border: "1px solid #E2E7EF",
    boxShadow: "0 20px 40px rgba(30, 60, 90, 0.1)",
    overflow: "hidden",
  },
  mockupWindowHeader: {
    padding: "0.75rem 1.25rem",
    background: "#F8F9FC",
    borderBottom: "1px solid #E2E7EF",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  windowDots: {
    display: "flex",
    gap: "0.4rem",
  },
  windowTitle: {
    fontSize: "0.8125rem",
    fontWeight: "600",
    color: "#5E7187",
  },
  userAvatar: {
    fontSize: "0.9rem",
  },
  mockupBody: {
    display: "flex",
    minHeight: "340px",
  },
  mockupSidebar: {
    width: "140px",
    background: "#F8F9FC",
    borderRight: "1px solid #E2E7EF",
    padding: "1rem 0.5rem",
    display: "flex",
    flexDirection: "column",
    gap: "0.4rem",
  },
  sidebarItem: {
    padding: "0.45rem 0.75rem",
    borderRadius: "6px",
    fontSize: "0.75rem",
    color: "#5E7187",
    fontWeight: "500",
  },
  mockupContent: {
    flex: 1,
    padding: "1.25rem",
    display: "flex",
    flexDirection: "column",
    gap: "0.85rem",
    background: "#FFFFFF",
  },
  mockupHeaderRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  mockupMetaRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    fontSize: "0.75rem",
    flexWrap: "wrap",
  },
  mockupTopicTag: {
    background: "#F1F4F9",
    padding: "0.15rem 0.5rem",
    borderRadius: "4px",
    color: "#5E7187",
    fontSize: "0.725rem",
  },
  mockupDiffTag: {
    background: "#FFF7DF",
    color: "#C58A27",
    padding: "0.15rem 0.5rem",
    borderRadius: "4px",
    fontWeight: "600",
    fontSize: "0.725rem",
  },
  mockupTimer: {
    marginLeft: "auto",
    color: "#102A43",
    fontWeight: "700",
  },
  mockupQuestionCard: {
    background: "#F8F9FC",
    borderRadius: "10px",
    border: "1px solid #E2E7EF",
    padding: "1rem",
  },
  mockupQuestionStatement: {
    fontSize: "0.875rem",
    fontWeight: "700",
    color: "#102A43",
    marginBottom: "1rem",
  },
  waveformBox: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    background: "#FFFFFF",
    borderRadius: "8px",
    padding: "0.75rem 1rem",
    border: "1px solid #E2E7EF",
  },
  waveformContainer: {
    display: "flex",
    alignItems: "center",
    gap: "0.35rem",
  },
  waveBar: {
    width: "4px",
    background: "#2F66C5",
    borderRadius: "2px",
  },
  mockupRecordBtn: {
    width: "28px",
    height: "28px",
    borderRadius: "50%",
    background: "#D35D5D",
    color: "#FFFFFF",
    border: "none",
    fontSize: "0.7rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  listeningText: {
    fontSize: "0.725rem",
    color: "#5E7187",
    textAlign: "center",
    marginTop: "0.4rem",
  },
  mockupMetricsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: "0.5rem",
  },
  mockupMetricBox: {
    background: "#F8F9FC",
    borderRadius: "8px",
    border: "1px solid #E2E7EF",
    padding: "0.5rem",
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
  },
  mockupMetricIcon: {
    width: "24px",
    height: "24px",
    borderRadius: "6px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "0.7rem",
  },
  mockupMetricLabel: {
    fontSize: "0.65rem",
    color: "#5E7187",
  },
  mockupMetricVal: {
    fontSize: "0.8rem",
    fontWeight: "800",
    color: "#102A43",
  },
  featureStripSection: {
    padding: "1.5rem 1.5rem 3.5rem 1.5rem",
  },
  sectionContainer: {
    maxWidth: "1240px",
    margin: "0 auto",
  },
  featureStripGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: "1.25rem",
  },
  featureStripCard: {
    background: "#FFFFFF",
    border: "1px solid #E2E7EF",
    borderRadius: "14px",
    padding: "1.5rem",
    boxShadow: "0 4px 20px rgba(30, 60, 90, 0.04)",
  },
  featureIconContainer: {
    width: "42px",
    height: "42px",
    borderRadius: "10px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: "1rem",
  },
  featureStripTitle: {
    fontSize: "1rem",
    fontWeight: "700",
    color: "#102A43",
    marginBottom: "0.35rem",
  },
  featureStripDesc: {
    fontSize: "0.875rem",
    color: "#5E7187",
    lineHeight: "1.4",
  },
  topicsSection: {
    padding: "3.5rem 1.5rem",
  },
  sectionHeader: {
    textAlign: "center",
    marginBottom: "2.5rem",
  },
  sectionTag: {
    color: "#2F66C5",
    fontSize: "0.75rem",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  sectionTitle: {
    fontSize: "1.85rem",
    fontWeight: "800",
    color: "#102A43",
    marginTop: "0.3rem",
    marginBottom: "0.4rem",
    letterSpacing: "-0.02em",
  },
  sectionSubtitle: {
    color: "#5E7187",
    fontSize: "0.95rem",
  },
  topicsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(270px, 1fr))",
    gap: "1.25rem",
    marginBottom: "2.5rem",
  },
  topicCard: {
    background: "#FFFFFF",
    border: "1px solid #E2E7EF",
    borderRadius: "14px",
    padding: "1.5rem",
    cursor: "pointer",
    boxShadow: "0 4px 20px rgba(30, 60, 90, 0.04)",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
  },
  topicCardSelected: {
    borderColor: "#2F66C5",
    boxShadow: "0 0 0 2px #2F66C5, 0 8px 25px rgba(47, 102, 197, 0.15)",
  },
  topicHeaderRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: "0.5rem",
    marginBottom: "0.75rem",
  },
  topicCardTitle: {
    fontSize: "1.1rem",
    fontWeight: "700",
    color: "#102A43",
    margin: 0,
  },
  questionCountBadge: {
    background: "#EAF2FF",
    border: "1px solid #D0E2FF",
    color: "#2F66C5",
    fontSize: "0.75rem",
    fontWeight: "700",
    padding: "0.25rem 0.6rem",
    borderRadius: "6px",
    whiteSpace: "nowrap",
  },
  topicCardDesc: {
    fontSize: "0.875rem",
    color: "#5E7187",
    lineHeight: "1.4",
    marginBottom: "1rem",
  },
  selectIndicator: {
    fontSize: "0.8125rem",
    fontWeight: "700",
  },
  prepareCard: {
    background: "#FFFFFF",
    border: "1px solid #E2E7EF",
    borderRadius: "16px",
    padding: "2rem",
    maxWidth: "650px",
    margin: "0 auto",
    boxShadow: "0 8px 30px rgba(30, 60, 90, 0.06)",
  },
  prepareHeader: {
    marginBottom: "1.25rem",
  },
  configForm: {
    display: "flex",
    flexDirection: "column",
    gap: "1.25rem",
  },
  inputGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "0.4rem",
  },
  label: {
    fontSize: "0.85rem",
    fontWeight: "600",
    color: "#102A43",
  },
  input: {
    padding: "0.75rem 1rem",
    borderRadius: "8px",
    background: "#F8F9FC",
    border: "1px solid #E2E7EF",
    color: "#102A43",
    fontSize: "0.95rem",
    outline: "none",
  },
  errorBanner: {
    padding: "0.75rem 1rem",
    background: "#FDEEEF",
    border: "1px solid #FAD2D4",
    color: "#D35D5D",
    borderRadius: "8px",
    fontSize: "0.875rem",
  },
  startBtn: {
    padding: "0.95rem 2rem",
    fontSize: "1rem",
    fontWeight: "700",
    borderRadius: "10px",
    background: "#2F66C5",
    color: "#ffffff",
    border: "none",
    boxShadow: "0 4px 15px rgba(47, 102, 197, 0.3)",
  },
  howSection: {
    padding: "4rem 1.5rem",
  },
  stepsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "1.25rem",
  },
  stepCard: {
    background: "#FFFFFF",
    border: "1px solid #E2E7EF",
    borderRadius: "14px",
    padding: "1.5rem",
    boxShadow: "0 4px 20px rgba(30, 60, 90, 0.04)",
  },
  stepHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "1rem",
  },
  stepBadgeNum: {
    width: "28px",
    height: "28px",
    borderRadius: "50%",
    background: "#EAF2FF",
    color: "#2F66C5",
    fontWeight: "800",
    fontSize: "0.85rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  stepIconBox: {
    width: "38px",
    height: "38px",
    borderRadius: "10px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  stepTitle: {
    fontSize: "1.05rem",
    fontWeight: "700",
    color: "#102A43",
    marginBottom: "0.4rem",
  },
  stepDesc: {
    fontSize: "0.875rem",
    color: "#5E7187",
    lineHeight: "1.4",
  },
  footer: {
    background: "#FFFFFF",
    borderTop: "1px solid #E2E7EF",
    padding: "1.75rem 1.5rem",
    marginTop: "2rem",
  },
  footerContainer: {
    maxWidth: "1240px",
    margin: "0 auto",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "1rem",
  },
  footerBrand: {
    fontWeight: "800",
    color: "#102A43",
    fontSize: "1rem",
  },
  footerSub: {
    color: "#5E7187",
    fontSize: "0.8125rem",
  },
  footerRights: {
    color: "#5E7187",
    fontSize: "0.8125rem",
  },
};
