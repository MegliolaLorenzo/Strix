import { useState } from "react";

interface FilterValues {
  verdict: string;
  minConfidence: number;
  maxConfidence: number;
}

interface FiltersProps {
  values: FilterValues;
  onChange: (v: FilterValues) => void;
  onExport: (f: "csv" | "json") => void;
}

const VERDICTS = [
  { val: "",              label: "All",            color: "#1D1D1F" },
  { val: "Supported",     label: "Supported",      color: "#34C759" },
  { val: "Unsupported",   label: "Unsupported",    color: "#FF3B30" },
  { val: "Misleading",    label: "Misleading",     color: "#FF9500" },
  { val: "Needs Context", label: "Needs Context",  color: "#007AFF" },
];

export default function Filters({ values, onChange, onExport }: FiltersProps) {
  const [confOpen, setConfOpen] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-2 mb-6 rounded-2xl bg-white/70 border border-white/80 p-2.5 shadow-sm">
      {/* Verdict pills */}
      <div className="flex items-center gap-1 flex-wrap">
        {VERDICTS.map((v) => {
          const active = values.verdict === v.val;
          return (
            <button
              key={v.val}
              onClick={() => onChange({ ...values, verdict: v.val })}
              className={`
                px-3.5 py-1.5 rounded-full text-[12px] font-semibold transition-all duration-200
                ${active
                  ? "text-white shadow-sm"
                  : "text-gray-500 bg-white/90 border border-gray-200 hover:border-gray-300 hover:text-gray-700"
                }
              `}
              style={active ? { backgroundColor: v.color } : undefined}
            >
              {v.label}
            </button>
          );
        })}
      </div>

      {/* Confidence range */}
      <div className="relative">
        <button
          onClick={() => setConfOpen(!confOpen)}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-[12px] font-medium
                     text-gray-500 bg-white/90 border border-gray-200 hover:border-gray-300
                     hover:text-gray-700 transition-all duration-200"
        >
          Confidence: {values.minConfidence}–{values.maxConfidence}%
          <svg className={`w-3 h-3 transition-transform ${confOpen ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {confOpen && (
          <div className="absolute top-full left-0 mt-1.5 bg-white rounded-xl shadow-lg border border-gray-200 p-3 z-10 animate-fade">
            <div className="flex items-center gap-2">
              <input
                type="number" min={0} max={100}
                value={values.minConfidence}
                onChange={(e) => onChange({ ...values, minConfidence: Number(e.target.value) })}
                className="w-14 text-center text-[12px] font-mono text-gray-700 border border-gray-200 rounded-lg px-2 py-1 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
              />
              <span className="text-gray-300 text-xs">to</span>
              <input
                type="number" min={0} max={100}
                value={values.maxConfidence}
                onChange={(e) => onChange({ ...values, maxConfidence: Number(e.target.value) })}
                className="w-14 text-center text-[12px] font-mono text-gray-700 border border-gray-200 rounded-lg px-2 py-1 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
              />
            </div>
          </div>
        )}
      </div>

      <div className="flex-1" />

      {/* Export */}
      {(["CSV", "JSON"] as const).map((f) => (
        <button
          key={f}
          onClick={() => onExport(f.toLowerCase() as "csv" | "json")}
          className="px-3.5 py-1.5 rounded-full text-[12px] font-semibold
                     text-gray-500 bg-white border border-gray-200
                     hover:border-gray-300 hover:text-gray-700
                     active:scale-95 transition-all duration-150"
        >
          {f}
        </button>
      ))}
    </div>
  );
}

export type { FilterValues };
