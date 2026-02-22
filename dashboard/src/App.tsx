import { useState } from "react";
import Timeline from "./pages/Timeline";
import Analytics from "./pages/Analytics";

type Page = "timeline" | "analytics";

export default function App() {
  const [page, setPage] = useState<Page>("timeline");

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#e7e8ef_0%,_#dadce6_42%,_#d6d7df_100%)] px-4 py-3 md:px-6 md:py-5">
      <div className="mx-auto w-full min-h-[calc(100vh-1.5rem)] rounded-[34px] border border-white/60 bg-[#eceef3]/80 backdrop-blur-sm shadow-[0_24px_80px_rgba(17,24,39,0.12)] px-4 pb-6 pt-4 md:px-8 md:pb-8 md:pt-6">
        <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 rounded-full bg-white px-4 py-2 shadow-sm">
              <span className="text-[18px]">🦉</span>
              <h1 className="text-[18px] font-bold tracking-tight text-[#111827]">STRIX</h1>
            </div>
            <div className="lg:hidden flex items-center gap-2 text-[12px] text-[#6B7280]">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/80" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
              </span>
              Live
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-full bg-white/70 p-1">
            {(["timeline", "analytics"] as const).map((id) => (
              <button
                key={id}
                onClick={() => setPage(id)}
                className={`px-4 py-2 rounded-full text-[13px] font-semibold transition-all ${
                  page === id
                    ? "bg-[#111827] text-white shadow-sm"
                    : "text-[#4B5563] hover:bg-white hover:text-[#111827]"
                }`}
              >
                {id === "timeline" ? "Timeline" : "Analytics"}
              </button>
            ))}
          </div>

          <div className="hidden lg:flex items-center gap-2 text-[12px] text-[#6B7280] font-semibold">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/80" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
            </span>
            Live
          </div>
        </header>

        <section className="mt-6 mb-5">
          <div>
            <h2 className="text-[38px] md:text-[48px] leading-[1.02] font-extrabold tracking-tight text-[#101828]">
              Cmd + Shift + X
            </h2>
            <p className="mt-2 text-[16px] text-[#4B5563]">
              Write something, use the shortcut, and without leaving your app verify whether it is correct or can be improved.
            </p>
          </div>
        </section>

        <main>
          {page === "timeline" && <Timeline />}
          {page === "analytics" && <Analytics />}
        </main>
      </div>
    </div>
  );
}
