import { useState, useEffect } from "react";
import { VerdictPieChart, DailyChart, DomainChart } from "../components/Charts";
import type { AnalyticsData } from "../components/Charts";

const EMPTY: AnalyticsData = {
  total_checks: 0, verdict_distribution: {}, daily_counts: [],
  top_claims: [], avg_confidence: 0, source_domains: {},
};

const V_COLOR: Record<string, string> = {
  Supported: "#34C759", Unsupported: "#FF3B30",
  Misleading: "#FF9500", "Needs Context": "#007AFF",
};
const V_BG: Record<string, string> = {
  Supported: "#F0FFF4", Unsupported: "#FFF5F5",
  Misleading: "#FFFBEB", "Needs Context": "#EFF6FF",
};

function Metric({ label, value, sub, delay = 0 }: {
  label: string; value: string; sub?: string; delay?: number;
}) {
  return (
    <div
      className="bg-white/90 border border-white rounded-3xl shadow-sm px-5 py-5 animate-in"
      style={{ animationDelay: `${delay}ms` }}
    >
      <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide mb-1.5">{label}</p>
      <p className="text-[28px] font-semibold text-gray-900 leading-none tracking-tight">{value}</p>
      {sub && <p className="text-[11px] text-gray-400 mt-1.5">{sub}</p>}
    </div>
  );
}

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData>(EMPTY);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/analytics")
      .then(r => r.ok ? r.json() : EMPTY)
      .then(setData)
      .catch(() => setData(EMPTY))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-60 gap-3">
      <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      <p className="text-[12px] text-gray-400">Loading</p>
    </div>
  );

  if (!data.total_checks) return (
    <div className="bg-white rounded-2xl shadow-sm flex flex-col items-center justify-center h-60 text-center gap-2">
      <p className="text-[15px] font-medium text-gray-600">No data yet</p>
      <p className="text-[13px] text-gray-400">Analytics appear after your first fact-check</p>
    </div>
  );

  const problematic = (data.verdict_distribution["Unsupported"] ?? 0) + (data.verdict_distribution["Misleading"] ?? 0);
  const pctProblematic = data.total_checks ? ((problematic / data.total_checks) * 100).toFixed(0) : "0";
  const uniqueDomains = Object.keys(data.source_domains).length;

  return (
    <div className="rounded-[28px] bg-[#F7F8FB]/95 border border-white p-5 md:p-6 shadow-sm space-y-4">
      <h2 className="text-[24px] font-semibold text-gray-900 tracking-tight animate-in mb-4">
        Analytics
      </h2>

      {/* Metrics row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 items-stretch">
        <Metric label="Total Checks" value={data.total_checks.toString()} delay={0} />
        <Metric label="Avg Confidence" value={`${data.avg_confidence}%`} delay={40} />
        <Metric
          label="Flagged"
          value={`${pctProblematic}%`}
          sub={`${problematic} of ${data.total_checks}`}
          delay={80}
        />
        <Metric label="Sources" value={uniqueDomains.toString()} delay={120} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="animate-in" style={{ animationDelay: "100ms" }}>
          <VerdictPieChart data={data.verdict_distribution} />
        </div>
        <div className="animate-in" style={{ animationDelay: "140ms" }}>
          <DailyChart data={data.daily_counts} />
        </div>
      </div>

      <div className="animate-in" style={{ animationDelay: "180ms" }}>
        <DomainChart data={data.source_domains} />
      </div>

      {/* Repeated claims */}
      {data.top_claims.length > 0 && (
        <div className="bg-white/90 border border-white rounded-[28px] shadow-sm overflow-hidden animate-in mt-4" style={{ animationDelay: "220ms" }}>
          <div className="px-5 py-4 border-b border-gray-100">
            <h3 className="text-[13px] font-semibold text-gray-800">Repeated Claims</h3>
          </div>
          <div className="divide-y divide-gray-50">
            {data.top_claims.map((c, i) => (
              <div key={i} className="flex items-center gap-4 px-5 py-3 hover:bg-gray-50/50 transition-colors">
                <span className="text-[11px] font-mono text-gray-400 bg-gray-50 px-1.5 py-0.5 rounded flex-shrink-0">
                  {c.cnt}x
                </span>
                <p className="text-[13px] text-gray-700 flex-1 truncate">
                  {c.claim}
                </p>
                <span
                  className="text-[11px] font-medium px-2 py-0.5 rounded flex-shrink-0"
                  style={{
                    backgroundColor: V_BG[c.verdict] ?? "#F5F5F7",
                    color: V_COLOR[c.verdict] ?? "#8E8E93",
                  }}
                >
                  {c.verdict}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
