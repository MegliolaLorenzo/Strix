import { useState } from "react";

interface Source {
  title: string;
  url: string;
  domain: string;
  relevance: string;
}

interface Check {
  id: string;
  claim: string;
  verdict: string;
  confidence: number;
  explanation: string;
  sources: Source[];
  rewrite_suggestion: string | null;
  checked_at: string;
  search_time_ms: number;
  analysis_time_ms: number;
}

const V_COLORS: Record<string, string> = {
  Supported: "#34C759",
  Unsupported: "#FF3B30",
  Misleading: "#FF9500",
  "Needs Context": "#007AFF",
};

const V_BG: Record<string, string> = {
  Supported: "#F0FFF4",
  Unsupported: "#FFF5F5",
  Misleading: "#FFFBEB",
  "Needs Context": "#EFF6FF",
};

export default function VerdictCard({ check, index = 0 }: { check: Check; index?: number }) {
  const [expanded, setExpanded] = useState(false);
  const color = V_COLORS[check.verdict] ?? "#8E8E93";
  const bg = V_BG[check.verdict] ?? "#F5F5F7";
  const totalS = ((check.search_time_ms + check.analysis_time_ms) / 1000).toFixed(1);
  const confColor = check.confidence >= 70 ? "#34C759" : check.confidence >= 40 ? "#FF9500" : "#FF3B30";

  const when = new Date(check.checked_at).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });

  return (
    <div
      className="bg-white/90 border border-white rounded-3xl shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden animate-in"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      {/* Main row — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-5 py-4 flex items-start gap-4 group"
      >
        {/* Verdict dot */}
        <span
          className="w-2.5 h-2.5 rounded-full flex-shrink-0 mt-1.5"
          style={{ backgroundColor: color }}
        />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className="text-[14px] text-gray-800 leading-relaxed line-clamp-2">
            {check.claim}
          </p>
          <div className="flex items-center gap-3 mt-2">
            <span
              className="text-[11px] font-semibold px-2 py-0.5 rounded-md"
              style={{ color, backgroundColor: bg }}
            >
              {check.verdict}
            </span>
            <span className="text-[11px] font-mono text-gray-400">
              {check.confidence}%
            </span>
            <span className="text-[11px] text-gray-300">{totalS}s</span>
            <span className="text-[11px] text-gray-300">{when}</span>
          </div>
        </div>

        {/* Expand indicator */}
        <svg
          className={`w-4 h-4 text-gray-300 flex-shrink-0 mt-1.5 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="px-5 pb-5 pt-0 space-y-4 animate-fade">
          {/* Confidence bar */}
          <div className="flex items-center gap-3 pl-6">
            <div className="flex-1 h-1 rounded-full bg-gray-100 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700 ease-out"
                style={{ width: `${check.confidence}%`, backgroundColor: confColor }}
              />
            </div>
            <span className="text-[11px] font-mono font-medium w-8 text-right" style={{ color: confColor }}>
              {check.confidence}%
            </span>
          </div>

          {/* Explanation */}
          <div className="pl-6">
            <p className="text-[13px] text-gray-600 leading-relaxed">
              {check.explanation}
            </p>
          </div>

          {/* Rewrite suggestion */}
          {check.rewrite_suggestion && (
            <div className="ml-6 rounded-xl px-4 py-3 bg-green-50 border border-green-100">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-green-600 mb-1">
                Suggested rewrite
              </p>
              <p className="text-[13px] text-green-800 leading-relaxed">
                {check.rewrite_suggestion}
              </p>
            </div>
          )}

          {/* Sources */}
          {check.sources.length > 0 && (
            <div className="pl-6 space-y-1.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-2">
                Sources
              </p>
              {check.sources.map((s, i) => (
                <a
                  key={i}
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={s.relevance}
                  className="flex items-center gap-2.5 group/link"
                >
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-50 border border-gray-100 text-gray-500 flex-shrink-0 group-hover/link:border-blue-200 group-hover/link:text-blue-500 transition-colors">
                    {s.domain}
                  </span>
                  <span className="text-[12px] text-gray-500 group-hover/link:text-blue-600 truncate transition-colors">
                    {s.title.length > 80 ? s.title.slice(0, 80) + "..." : s.title}
                  </span>
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export type { Check };
