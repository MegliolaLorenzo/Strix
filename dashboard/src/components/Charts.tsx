import {
  PieChart, Pie, Cell, ResponsiveContainer, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";

interface AnalyticsData {
  total_checks: number;
  verdict_distribution: Record<string, number>;
  daily_counts: { day: string; cnt: number }[];
  top_claims: { claim: string; verdict: string; confidence: number; cnt: number }[];
  avg_confidence: number;
  source_domains: Record<string, number>;
}

const COLORS: Record<string, string> = {
  Supported: "#34C759",
  Unsupported: "#FF3B30",
  Misleading: "#FF9500",
  "Needs Context": "#007AFF",
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-100 px-3 py-2 text-[12px]">
      {label && <p className="text-gray-400 text-[11px] mb-1">{label}</p>}
      {payload.map((p: any, i: number) => (
        <p key={i} className="font-medium" style={{ color: p.color ?? "#1D1D1F" }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  );
};

function Card({ title, children, className = "" }: {
  title: string; children: React.ReactNode; className?: string;
}) {
  return (
    <div className={`bg-white/90 border border-white rounded-3xl shadow-sm p-5 ${className}`}>
      <h3 className="text-[13px] font-semibold text-gray-800 mb-4 tracking-wide">{title}</h3>
      {children}
    </div>
  );
}

export function VerdictPieChart({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data).map(([name, value]) => ({ name, value }));
  const total = chartData.reduce((s, d) => s + d.value, 0);

  return (
    <Card title="Verdict Distribution">
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={chartData} cx="50%" cy="50%"
            innerRadius={55} outerRadius={80}
            paddingAngle={2} dataKey="value"
            startAngle={90} endAngle={450}
            stroke="none"
          >
            {chartData.map((e) => (
              <Cell key={e.name} fill={COLORS[e.name] ?? "#D2D2D7"} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <text x="50%" y="48%" textAnchor="middle" className="text-[22px] font-semibold fill-gray-800">
            {total}
          </text>
          <text x="50%" y="58%" textAnchor="middle" className="text-[11px] fill-gray-400">
            total
          </text>
        </PieChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap gap-4 justify-center mt-2">
        {chartData.map((d) => (
          <div key={d.name} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: COLORS[d.name] ?? "#D2D2D7" }} />
            <span className="text-[11px] text-gray-500">{d.name}</span>
            <span className="text-[11px] font-mono text-gray-400">{d.value}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function DailyChart({ data }: { data: { day: string; cnt: number }[] }) {
  const sorted = [...data].reverse();
  return (
    <Card title="Daily Activity">
      <ResponsiveContainer width="100%" height={210}>
        <AreaChart data={sorted} margin={{ top: 14, left: -20, right: 8, bottom: 0 }}>
          <defs>
            <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#007AFF" stopOpacity={0.12} />
              <stop offset="100%" stopColor="#007AFF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" vertical={false} />
          <XAxis
            dataKey="day" tick={{ fontSize: 11, fill: "#AEAEB2" }}
            tickFormatter={(v) => v.slice(5)}
            axisLine={false} tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#AEAEB2" }}
            domain={[0, (dataMax: number) => Math.max(1, dataMax + 1)]}
            allowDecimals={false} axisLine={false} tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone" dataKey="cnt" stroke="#007AFF" strokeWidth={2}
            fill="url(#gradient)" name="Checks"
            dot={{ r: 2.5, fill: "#007AFF", strokeWidth: 0 }}
            activeDot={{ r: 4, fill: "#0055CC", strokeWidth: 0 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function DomainChart({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8)
    .map(([domain, count]) => ({ domain, count }));

  const max = chartData[0]?.count ?? 1;

  return (
    <Card title="Top Sources">
      <div className="space-y-2.5">
        {chartData.map((d, i) => (
          <div key={d.domain} className="flex items-center gap-3">
            <span className="text-[11px] text-gray-400 w-4 text-right font-mono">{i + 1}</span>
            <span className="text-[12px] text-gray-600 w-32 truncate">{d.domain}</span>
            <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
              <div
                className="h-full rounded-full bg-gray-800 transition-all duration-500"
                style={{ width: `${(d.count / max) * 100}%` }}
              />
            </div>
            <span className="text-[11px] font-mono text-gray-400 w-6 text-right">{d.count}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

export type { AnalyticsData };
