import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";

export function KpiCard({ title, value, previous, status = "healthy" }: { title: string; value: string; previous?: number; status?: "healthy" | "warning" | "critical" }) {
  const delta = previous;
  const color = status === "critical" ? "border-red-500/40" : status === "warning" ? "border-amber-500/40" : "border-emerald-500/30";
  return (
    <div className={`rounded-lg border ${color} bg-panelSoft p-4`}>
      <p className="text-xs uppercase tracking-wide text-slate-400">{title}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
      {typeof delta === "number" && (
        <p className={`mt-2 flex items-center gap-1 text-xs ${delta > 0 ? "text-emerald-300" : delta < 0 ? "text-red-300" : "text-slate-400"}`}>
          {delta > 0 ? <ArrowUpRight className="h-3 w-3" /> : delta < 0 ? <ArrowDownRight className="h-3 w-3" /> : <ArrowRight className="h-3 w-3" />}
          {delta > 0 ? "+" : ""}{delta.toFixed(2)} vs previous
        </p>
      )}
    </div>
  );
}
