import { useState } from "react";
import { Bot, ChevronDown, ChevronRight } from "lucide-react";
import type { AgentEvent } from "../api/types";
import { titleize } from "../utils/formatters";
import { StatusBadge } from "./layout/StatusBadge";

const eventMeta: Record<string, { title: string; accent: string }> = {
  RED_PLAN: { title: "Red Agent Plan", accent: "border-red-500/50 bg-red-500/10" },
  BLUE_ASSESSMENT: { title: "Blue Agent Assessment", accent: "border-blue-500/50 bg-blue-500/10" },
  BLUE_REVISED_PLAN: { title: "Blue Agent Revised Final Plan", accent: "border-blue-400/50 bg-blue-500/10" },
  FINAL_ACTION: { title: "Final Action", accent: "border-blue-400/50 bg-blue-500/10" },
  EXECUTOR_ACTION: { title: "Executor-Narrator Executed Action", accent: "border-emerald-500/50 bg-emerald-500/10" },
  EXECUTION_RESULT: { title: "Execution Result", accent: "border-emerald-400/40 bg-emerald-500/5" },
  KPI_EVALUATION: { title: "KPI Evaluation", accent: "border-amber-400/40 bg-amber-500/10" },
  NARRATION: { title: "Narration", accent: "border-cyan-400/50 bg-cyan-500/10" },
  MEMORY_LESSON: { title: "Memory Lesson", accent: "border-violet-400/50 bg-violet-500/10" },
};

function chips(label: string, values?: any[]) {
  if (!Array.isArray(values) || values.length === 0) return null;
  return (
    <div>
      <p className="mb-1 text-[11px] uppercase text-slate-500">{label}</p>
      <div className="flex flex-wrap gap-1">
        {values.map((value, index) => (
          <span key={`${label}-${index}`} className="rounded-full border border-line bg-command px-2 py-0.5 text-xs text-slate-300">
            {String(value)}
          </span>
        ))}
      </div>
    </div>
  );
}

function section(label: string, value?: any) {
  if (value === undefined || value === null) return null;
  const text = Array.isArray(value) ? value.join(" · ") : typeof value === "object" ? JSON.stringify(value) : String(value);
  if (!text) return null;
  return (
    <div className="rounded-md border border-line bg-command/70 p-3 text-sm">
      <p className="mb-1 text-[11px] uppercase text-slate-500">{label}</p>
      <p className="text-slate-300">{text}</p>
    </div>
  );
}

export function AgentEventCard({ event }: { event: AgentEvent }) {
  const [open, setOpen] = useState(false);
  const meta = eventMeta[event.event_type] || { title: titleize(event.event_type), accent: "border-line bg-command" };
  const payload = event.payload || {};
  const tradeoffs = payload.expected_tradeoffs || payload.tradeoff_summary || {};
  const isNarration = event.event_type === "NARRATION";

  return (
    <article className={`rounded-lg border p-4 ${meta.accent}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-slate-300" />
            <h3 className={`${isNarration ? "text-lg" : "text-sm"} font-semibold text-slate-100`}>{meta.title}</h3>
          </div>
          <p className="mt-1 text-xs text-slate-400">{titleize(event.agent_id)} · {event.created_at ? new Date(event.created_at).toLocaleString() : "pending time"}</p>
        </div>
        <StatusBadge status={event.event_type.toLowerCase()} />
      </div>

      <p className="mt-3 font-medium text-slate-100">{event.title}</p>
      <p className={`mt-2 ${isNarration ? "text-base leading-7 text-cyan-50" : "text-sm text-slate-300"}`}>{event.summary}</p>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {section("what red observed", payload.observation || payload.observed_problem)}
        {section("candidate actions considered", payload.candidate_actions)}
        {section("initial recommended action", payload.initial_recommended_action || payload.recommended_action)}
        {section("risks blue identified", payload.risks_identified)}
        {section("what blue changed", payload.what_changed || payload.revisions)}
        {section("final action selected", payload.final_action || payload.request)}
        {section("why revised plan is safer", payload.why_safer || payload.why_better)}
        {chips("improves", tradeoffs.improves)}
        {chips("worsens", tradeoffs.worsens)}
        {chips("neutral", tradeoffs.neutral)}
        {chips("constraints", payload.constraint_violations)}
      </div>

      {(payload.confidence !== undefined || payload.expected_kpi_delta) && (
        <div className="mt-3 rounded-md border border-line bg-command/70 p-3 text-sm">
          {payload.confidence !== undefined && <p>Confidence: <strong>{Math.round(Number(payload.confidence) * 100)}%</strong></p>}
          {payload.expected_kpi_delta && <p className="mt-1 text-slate-400">Expected KPI delta attached in payload.</p>}
        </div>
      )}

      {event.event_type === "EXECUTOR_ACTION" && (
        <div className="mt-3 rounded-md border border-line bg-command/70 p-3 text-sm">
          <p>Endpoint: <strong>{payload.endpoint || payload.execute_endpoint || "not supplied"}</strong></p>
          <p className="mt-1 text-slate-400">Request/response are available in JSON payload.</p>
        </div>
      )}

      <button onClick={() => setOpen(!open)} className="mt-3 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-100">
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />} JSON payload
      </button>
      {open && <pre className="mt-2 max-h-80 overflow-auto rounded-md bg-[#050a10] p-3 text-xs text-slate-300">{JSON.stringify(payload, null, 2)}</pre>}
    </article>
  );
}
