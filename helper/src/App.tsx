import { useState, useEffect } from "react";
import { listen } from "@tauri-apps/api/event";
import { readText } from "@tauri-apps/plugin-clipboard-manager";

interface Source {
  title: string;
  url: string;
  domain: string;
  relevance: string;
}

interface Verdict {
  id: string;
  claim: string;
  verdict: "Supported" | "Unsupported" | "Misleading" | "Needs Context";
  confidence: number;
  explanation: string;
  sources: Source[];
  rewrite_suggestion: string | null;
  checked_at: string;
  search_time_ms: number;
  analysis_time_ms: number;
}

type AppState = "idle" | "loading" | "result" | "error";

const VERDICT_COLORS: Record<string, string> = {
  Supported: "#22c55e",
  Unsupported: "#ef4444",
  Misleading: "#f59e0b",
  "Needs Context": "#3b82f6",
};

const VERDICT_ICONS: Record<string, string> = {
  Supported: "\u2713",
  Unsupported: "\u2717",
  Misleading: "\u26a0",
  "Needs Context": "\u2139",
};

export default function App() {
  const [state, setState] = useState<AppState>("idle");
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [error, setError] = useState<string>("");
  const [claim, setClaim] = useState<string>("");

  useEffect(() => {
    // Listen for the trigger from the Rust backend (global shortcut pressed)
    const unlisten = listen("trigger-check", async () => {
      // Read selected text from clipboard
      const text = await readText().catch(() => "");
      if (!text || !text.trim()) return;
      setClaim(text);
      setState("loading");
      setError("");
      setVerdict(null);

      try {
        const response = await fetch("http://127.0.0.1:8000/api/check", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${response.status}`);
        }

        const result: Verdict = await response.json();
        setVerdict(result);
        setState("result");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error");
        setState("error");
      }
    });

    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  if (state === "idle") {
    return (
      <div style={styles.container}>
        <div style={styles.idle}>
          <div style={styles.logo}>STRIX</div>
          <p style={styles.subtitle}>Select text and press Cmd+Shift+X</p>
        </div>
      </div>
    );
  }

  if (state === "loading") {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>
          <div style={styles.spinner} />
          <p style={styles.loadingText}>Checking claim...</p>
          <p style={styles.claimPreview}>
            "{claim.length > 80 ? claim.slice(0, 80) + "..." : claim}"
          </p>
        </div>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div style={styles.container}>
        <div style={styles.errorBox}>
          <p style={styles.errorTitle}>Check failed</p>
          <p style={styles.errorText}>{error}</p>
          <button style={styles.dismissBtn} onClick={() => setState("idle")}>
            Dismiss
          </button>
        </div>
      </div>
    );
  }

  if (!verdict) return null;

  const color = VERDICT_COLORS[verdict.verdict] || "#6b7280";
  const icon = VERDICT_ICONS[verdict.verdict] || "?";
  const totalTime = verdict.search_time_ms + verdict.analysis_time_ms;

  return (
    <div style={styles.container}>
      <div style={styles.resultCard}>
        {/* Header */}
        <div style={{ ...styles.header, borderLeftColor: color }}>
          <span style={{ ...styles.verdictIcon, color }}>{icon}</span>
          <div>
            <div style={{ ...styles.verdictLabel, color }}>
              {verdict.verdict}
            </div>
            <div style={styles.confidence}>
              Confidence: {verdict.confidence}%
            </div>
          </div>
          <button style={styles.closeBtn} onClick={() => setState("idle")}>
            x
          </button>
        </div>

        {/* Claim */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Claim</div>
          <p style={styles.claimText}>
            "{verdict.claim.length > 150
              ? verdict.claim.slice(0, 150) + "..."
              : verdict.claim}"
          </p>
        </div>

        {/* Explanation */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Analysis</div>
          <p style={styles.explanation}>{verdict.explanation}</p>
        </div>

        {/* Sources */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            Sources ({verdict.sources.length})
          </div>
          <div style={styles.sourcesList}>
            {verdict.sources.map((s, i) => (
              <a
                key={i}
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                style={styles.sourceLink}
              >
                <span style={styles.sourceDomain}>{s.domain}</span>
                <span style={styles.sourceTitle}>{s.title}</span>
              </a>
            ))}
          </div>
        </div>

        {/* Rewrite */}
        {verdict.rewrite_suggestion && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>Suggested rewrite</div>
            <p style={styles.rewrite}>{verdict.rewrite_suggestion}</p>
          </div>
        )}

        {/* Footer */}
        <div style={styles.footer}>
          Completed in {(totalTime / 1000).toFixed(1)}s
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: "100%",
    minHeight: "100vh",
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "center",
    padding: 16,
    background: "rgba(0,0,0,0.02)",
  },
  idle: {
    textAlign: "center",
    padding: 40,
    color: "#64748b",
  },
  logo: {
    fontSize: 28,
    fontWeight: 800,
    letterSpacing: 4,
    color: "#1e293b",
    marginBottom: 8,
  },
  subtitle: { fontSize: 13, color: "#94a3b8" },
  loading: {
    textAlign: "center",
    padding: 40,
  },
  spinner: {
    width: 32,
    height: 32,
    border: "3px solid #e2e8f0",
    borderTopColor: "#3b82f6",
    borderRadius: "50%",
    margin: "0 auto 16px",
    animation: "spin 0.8s linear infinite",
  },
  loadingText: { fontSize: 15, fontWeight: 600, color: "#334155" },
  claimPreview: {
    fontSize: 12,
    color: "#94a3b8",
    marginTop: 8,
    fontStyle: "italic",
  },
  errorBox: {
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: 8,
    padding: 20,
    textAlign: "center",
    width: "100%",
  },
  errorTitle: { fontSize: 15, fontWeight: 600, color: "#dc2626", marginBottom: 8 },
  errorText: { fontSize: 13, color: "#7f1d1d", marginBottom: 12 },
  dismissBtn: {
    background: "#dc2626",
    color: "white",
    border: "none",
    borderRadius: 6,
    padding: "6px 16px",
    fontSize: 13,
    cursor: "pointer",
  },
  resultCard: {
    background: "white",
    borderRadius: 10,
    boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
    width: "100%",
    maxWidth: 420,
    overflow: "hidden",
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "14px 16px",
    borderLeft: "4px solid",
    background: "#f8fafc",
  },
  verdictIcon: { fontSize: 28, fontWeight: 700 },
  verdictLabel: { fontSize: 17, fontWeight: 700 },
  confidence: { fontSize: 12, color: "#64748b" },
  closeBtn: {
    marginLeft: "auto",
    background: "none",
    border: "none",
    fontSize: 18,
    cursor: "pointer",
    color: "#94a3b8",
    padding: 4,
  },
  section: { padding: "10px 16px", borderTop: "1px solid #f1f5f9" },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 600,
    textTransform: "uppercase" as const,
    color: "#94a3b8",
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  claimText: { fontSize: 13, color: "#475569", fontStyle: "italic" },
  explanation: { fontSize: 13, color: "#334155", lineHeight: 1.5 },
  sourcesList: { display: "flex", flexDirection: "column" as const, gap: 6 },
  sourceLink: {
    display: "flex",
    gap: 8,
    alignItems: "center",
    textDecoration: "none",
    fontSize: 12,
    color: "#2563eb",
    padding: "4px 0",
  },
  sourceDomain: {
    background: "#eff6ff",
    padding: "2px 6px",
    borderRadius: 4,
    fontSize: 10,
    color: "#3b82f6",
    flexShrink: 0,
  },
  sourceTitle: {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap" as const,
  },
  rewrite: {
    fontSize: 13,
    color: "#166534",
    background: "#f0fdf4",
    padding: 10,
    borderRadius: 6,
    lineHeight: 1.5,
  },
  footer: {
    padding: "8px 16px",
    fontSize: 11,
    color: "#94a3b8",
    textAlign: "center" as const,
    borderTop: "1px solid #f1f5f9",
  },
};
