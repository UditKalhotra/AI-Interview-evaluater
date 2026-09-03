"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [status, setStatus] = useState("checking");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => {
        if (!res.ok) throw new Error(`Backend responded with ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setHealth(data);
        setStatus("connected");
      })
      .catch(() => setStatus("error"));
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", padding: "3rem" }}>
      <h1>Voice Interview System</h1>

      {status === "checking" && <p>Checking backend connection...</p>}

      {status === "connected" && (
        <>
          <p>Backend connected</p>
          <p>
            Database:{" "}
            {health?.database?.connected
              ? `connected (${health.database.name})`
              : "not connected — start mongod locally"}
          </p>
        </>
      )}

      {status === "error" && (
        <p>
          Could not reach the backend at {API_URL}. Make sure it&apos;s
          running (uvicorn app.main:app --reload).
        </p>
      )}
    </main>
  );
}
