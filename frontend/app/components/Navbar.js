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
            <span style={styles.brandTitle}>TalentEval</span>
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
              Home
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
            <Link 
              href="/#topic-selection" 
              style={{
                ...styles.link,
                ...(pathname === "/#topic-selection" ? styles.activeLink : {})
              }}
            >
              Topics
            </Link>
            <Link 
              href="/#how-it-works" 
              style={styles.link}
            >
              About
            </Link>
          </div>

          {/* System Health Badge */}
          <div style={styles.statusBadge}>
            <span
              style={{
                ...styles.statusDot,
                background:
                  status === "connected"
                    ? "#3D9468"
                    : status === "checking"
                    ? "#C58A27"
                    : "#D35D5D",
              }}
            />
            <span style={styles.statusText}>
              {status === "connected" && "System Online"}
              {status === "checking" && "Connecting..."}
              {status === "error" && "Offline"}
            </span>
          </div>

          <Link href="/#topic-selection" style={styles.btnGetStarted}>
            Get Started
          </Link>
        </div>
      </div>
    </nav>
  );
}

const styles = {
  nav: {
    background: "#FFFFFF",
    borderBottom: "1px solid #E2E7EF",
    position: "sticky",
    top: 0,
    zIndex: 50,
    boxShadow: "0 2px 10px rgba(15, 39, 66, 0.03)",
  },
  container: {
    maxWidth: "1240px",
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
    width: "36px",
    height: "36px",
    borderRadius: "8px",
    background: "#2F66C5",
    color: "#ffffff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: "800",
    fontSize: "0.95rem",
    letterSpacing: "-0.02em",
  },
  brandText: {
    display: "flex",
    flexDirection: "column",
  },
  brandTitle: {
    fontSize: "1.05rem",
    fontWeight: "800",
    color: "#102A43",
    lineHeight: "1.2",
  },
  brandSubtitle: {
    fontSize: "0.75rem",
    color: "#5E7187",
    fontWeight: "500",
  },
  rightSection: {
    display: "flex",
    alignItems: "center",
    gap: "1.25rem",
  },
  navLinks: {
    display: "flex",
    alignItems: "center",
    gap: "1.5rem",
  },
  link: {
    color: "#5E7187",
    fontSize: "0.9rem",
    fontWeight: "500",
    transition: "color 0.2s ease",
  },
  activeLink: {
    color: "#102A43",
    fontWeight: "700",
    borderBottom: "2px solid #2F66C5",
    paddingBottom: "0.2rem",
  },
  statusBadge: {
    display: "flex",
    alignItems: "center",
    gap: "0.45rem",
    padding: "0.35rem 0.75rem",
    borderRadius: "9999px",
    background: "#EAF7F0",
    border: "1px solid #C6EAD6",
  },
  statusDot: {
    width: "7px",
    height: "7px",
    borderRadius: "50%",
  },
  statusText: {
    fontSize: "0.8rem",
    fontWeight: "600",
    color: "#3D9468",
  },
  btnGetStarted: {
    padding: "0.5rem 1.25rem",
    borderRadius: "8px",
    background: "#2F66C5",
    color: "#ffffff",
    fontSize: "0.875rem",
    fontWeight: "600",
    textDecoration: "none",
    boxShadow: "0 2px 8px rgba(47, 102, 197, 0.25)",
  },
};
