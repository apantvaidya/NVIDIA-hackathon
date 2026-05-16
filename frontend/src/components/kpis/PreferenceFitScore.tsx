import type { AnyRecord, OptimizationProfile } from "../../api/types";
import { calculatePreferenceFit } from "../../utils/preferenceScoring";
import { SectionCard } from "../layout/SectionCard";

export function PreferenceFitScore({ kpis, profile }: { kpis?: AnyRecord; profile: OptimizationProfile }) {
  const result = calculatePreferenceFit(kpis, profile);
  return (
    <SectionCard title="Preference Fit Score" subtitle="Preference Fit measures how well the current simulation state matches your selected priorities. It is not a universal optimum.">
      <div className="flex items-end gap-4">
        <div className="text-5xl font-semibold text-emerald-200">{result.overall}</div>
        <div className="mb-1 text-sm text-slate-400">/ 100 alignment</div>
      </div>
      <div className="mt-4 space-y-2">
        {Object.entries(result.scores).map(([key, value]) => (
          <div key={key}>
            <div className="mb-1 flex justify-between text-xs text-slate-400"><span>{key}</span><span>{Math.round(value)}</span></div>
            <div className="h-2 rounded-full bg-command"><div className="h-2 rounded-full bg-emerald-400" style={{ width: `${value}%` }} /></div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}
