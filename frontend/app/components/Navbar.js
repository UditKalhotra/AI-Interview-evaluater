"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Navbar() {
  const pathname = usePathname();
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => {
        if (!res.ok) throw new Error("Health check failed");
        return res.json();
      })
      .then((data) => {
        if (data?.status === "ok") {
          setStatus("connected");
        } else {
          setStatus("error");
        }
      })
      .catch(() => setStatus("error"));
  }, []);

  return (
    <nav style={styles.nav}>
      <div style={styles.container}>
        {/* Brand / Logo */}
        <Link href="/" style={styles.brand}>
          <div style={styles.logoIcon}>TE</div>
          <div style={styles.brandText}>
            <span style={styles.brandTitle}>TalentEval AI</span>
            <span style={styles.brandSubtitle}>Technical Assessment Platform</span>
          </div>
        </Link>

        {/* Links & System Status */}
        <div style={styles.rightSection}>
          <div style={styles.navLinks}>
            <Link 
              href="/" 
              style={{
                ...styles.link,
                ...(pathname === "/" ? styles.activeLink : {})
              }}
            >
              Overview
            </Link>
            <Link 
              href="/#how-it-works" 
              style={{
                ...styles.link,
                ...(pathname === "/#how-it-works" ? styles.activeLink : {})
              }}
            >
              How It Works
            </Link>
          </div>

          {/* System Health Badge */}
          <div style={styles.statusBadge}>
            <span
              style={{
                ...styles.statusDot,
                background:
                  status === "connected"
                    ? "#10b981"
                    : status === "checking"
                    ? "#f59e0b"
                    : "#ef4444",
              }}
            />
            <span style={styles.statusText}>
              {status === "connected" && "System Online"}
              {status === "checking" && "Connecting..."}
              {status === "error" && "Offline"}
            </span>
          </div>
        </div>
      </div>
    </nav>
  );
}

const styles = {
  nav: {
    background: "#0f1724",
    borderBottom: "1px solid #233044",
    position: "sticky",
    top: 0,
    zIndex: 50,
    backdropFilter: "blur(12px)",
  },
  container: {
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "0.85rem 1.5rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
    textDecoration: "none",
  },
  logoIcon: {
    width: "38px",
    height: "38px",
    borderRadius: "8px",
    background: "linear-gradient(135deg, #2563eb 0%, #4f46e5 100%)",
    color: "#ffffff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: "800",
    fontSize: "1rem",
    letterSpacing: "-0.03em",
  },
  brandText: {
    display: "flex",
    flexDirection: "column",
  },
  brandTitle: {
    fontSize: "1.1rem",
    fontWeight: "700",
    color: "#f8fafc",
    lineHeight: "1.2",
  },
  brandSubtitle: {
    fontSize: "0.75rem",
    color: "#64748b",
    fontWeight: "500",
  },
  rightSection: {
    display: "flex",
    alignItems: "center",
    gap: "1.5rem",
  },
  navLinks: {
    display: "flex",
    alignItems: "center",
    gap: "1.25rem",
  },
  link: {
    color: "#94a3b8",
    fontSize: "0.9rem",
    fontWeight: "500",
    transition: "color 0.2s ease",
  },
  activeLink: {
    color: "#f8fafc",
    fontWeight: "600",
  },
  statusBadge: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.35rem 0.75rem",
    borderRadius: "9999px",
    background: "#151d2a",
    border: "1px solid #233044",
  },
  statusDot: {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
  },
  statusText: {
    fontSize: "0.8rem",
    fontWeight: "600",
    color: "#cbd5e1",
  },
};
