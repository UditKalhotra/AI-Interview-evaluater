"use client";

import { useEffect, useState } from "react";
import Avatar from "../components/Avatar";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Module 3 dev test harness.
 *
 * This page is ONLY here so you can manually confirm the avatar
 * question-audio flow works end-to-end (fetch question -> synthesize ->
 * play). It is NOT the final candidate-facing interview screen — that gets
 * assembled in Module 11, driven by the session/orchestration flow from
 * Modules 8-9, with no question picker and no visible question list.
 *
 * The question_id dropdown below is a developer tool for testing, not part
 * of the voice-only candidate experience.
 */
export default function InterviewTestHarness() {
  const [questions, setQuestions] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/questions`)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load questions (${res.status})`);
        return res.json();
      })
      .then((data) => {
        setQuestions(data);
        if (data.length > 0) setSelectedId(data[0].question_id);
      })
      .catch((err) => setLoadError(err.message));
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", padding: "3rem" }}>
      <h1>Module 3 — Avatar Voice Output (test harness)</h1>
      <p style={{ color: "#777" }}>
        Dev-only page. Pick a question_id to confirm the backend synthesizes
        and streams audio, and the avatar auto-plays it.
      </p>

      {loadError && (
        <p style={{ color: "crimson" }}>
          Could not load questions from {API_URL}/questions: {loadError}
        </p>
      )}

      {questions.length > 0 && (
        <select
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          style={{ padding: "0.5rem", fontSize: "1rem", marginBottom: "1rem" }}
        >
          {questions.map((q) => (
            <option key={q.question_id} value={q.question_id}>
              {q.question_id} ({q.topic})
            </option>
          ))}
        </select>
      )}

      {selectedId && <Avatar questionId={selectedId} />}
    </main>
  );
}
