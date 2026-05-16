import { SectionCard } from "../layout/SectionCard";
import { BeforeAfterComparison } from "./BeforeAfterComparison";

export function DecisionImpactPanel({ actions }: { actions: any[] }) {
  const latest = [...actions].reverse().find((item) => item.before_kpis || item.after_kpis || item.kpi_delta || item.tradeoff_summary);
  return (
    <SectionCard title="Decision Impact">
      {!latest ? (
        <p className="text-sm text-slate-400">Validated agent decisions will appear here once simulation or execution results include before/after KPI snapshots.</p>
      ) : (
        <div className="space-y-4">
          <div>
            <p className="text-sm font-semibold">{latest.action_type || "Simulation action"}</p>
            <p className="mt-1 text-xs text-slate-400">{JSON.stringify(latest.request || latest.payload || {}).slice(0, 180)}</p>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {["improves", "worsens", "neutral"].map((key) => (
              <div key={key} className="rounded-md bg-command p-3">
                <p className="text-xs uppercase text-slate-400">{key}</p>
                <p className="mt-2 text-sm text-slate-300">{(latest.tradeoff_summary?.[key] || []).slice(0, 5).join(", ") || "n/a"}</p>
              </div>
            ))}
          </div>
          <p className="text-sm text-slate-300">This action improved some metrics but worsened others.</p>
          <BeforeAfterComparison before={latest.before_kpis} after={latest.after_kpis} />
        </div>
      )}
    </SectionCard>
  );
}
