import { useState, useEffect, useCallback } from "react";
import VerdictCard from "../components/VerdictCard";
import type { Check } from "../components/VerdictCard";
import Filters from "../components/Filters";
import type { FilterValues } from "../components/Filters";

export default function Timeline() {
  const [checks, setChecks] = useState<Check[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<FilterValues>({
    verdict: "", minConfidence: 0, maxConfidence: 100,
  });

  const fetchChecks = useCallback(async () => {
    setLoading(true);
    const p = new URLSearchParams();
    if (filters.verdict) p.set("verdict", filters.verdict);
    if (filters.minConfidence > 0) p.set("min_confidence", String(filters.minConfidence));
    if (filters.maxConfidence < 100) p.set("max_confidence", String(filters.maxConfidence));
    try {
      const res = await fetch(`/api/checks?${p}`);
      if (res.ok) setChecks(await res.json());
    } catch { /* network error */ }
    finally { setLoading(false); }
  }, [filters]);

  useEffect(() => { fetchChecks(); }, [fetchChecks]);

  const handleExport = (format: "csv" | "json") => {
    if (!checks.length) return;
    let content: string, mime: string, filename: string;
    if (format === "json") {
      content = JSON.stringify(checks, null, 2);
      mime = "application/json";
      filename = "strix-checks.json";
    } else {
      const h = ["id", "claim", "verdict", "confidence", "explanation", "checked_at"];
      content = [h.join(","), ...checks.map(c =>
        h.map(k => `"${String(c[k as keyof Check] ?? "").replace(/"/g, '""')}"`).join(",")
      )].join("\n");
      mime = "text/csv";
      filename = "strix-checks.csv";
    }
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([content], { type: mime }));
    a.download = filename;
    a.click();
  };

  return (
    <div className="rounded-[28px] bg-[#F7F8FB]/95 border border-white p-5 md:p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-5 animate-in">
        <div>
          <h2 className="text-[24px] font-semibold text-gray-900 tracking-tight">
            Timeline
          </h2>
          {!loading && (
            <p className="text-[12px] text-gray-500 mt-0.5">
              {checks.length} check{checks.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>
        <button
          onClick={fetchChecks}
          className="px-4 py-2 rounded-full text-[12px] font-semibold
                     text-gray-600 bg-white border border-gray-200
                     hover:border-gray-300 hover:text-gray-800
                     active:scale-95 transition-all duration-150 shadow-sm"
        >
          Refresh
        </button>
      </div>

      <Filters values={filters} onChange={setFilters} onExport={handleExport} />

      {loading ? (
        <div className="flex flex-col items-center justify-center h-60 gap-3">
          <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
          <p className="text-[12px] text-gray-400">Loading</p>
        </div>
      ) : !checks.length ? (
        <div className="bg-white rounded-3xl shadow-sm flex flex-col items-center justify-center h-60 text-center gap-2">
          <p className="text-[15px] font-medium text-gray-600">No checks yet</p>
          <p className="text-[13px] text-gray-400">
            Select text and press{" "}
            <kbd className="font-mono text-[11px] bg-gray-100 px-1.5 py-0.5 rounded border border-gray-200">
              Cmd+Shift+X
            </kbd>
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {checks.map((check, i) => (
            <VerdictCard key={check.id} check={check} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
