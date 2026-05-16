import type { OptimizationProfile } from "../../api/types";
import { PROFILES } from "../../hooks/useOptimizationProfile";
import { formatPercent } from "../../utils/formatters";
import { SectionCard } from "../layout/SectionCard";

export function OptimizationPreferences({ profile, onSelect }: { profile: OptimizationProfile; onSelect: (name: string) => void }) {
  return (
    <SectionCard title="Optimization Preferences" subtitle="Frontend-only priorities. The backend never optimizes against these.">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
        {PROFILES.map((item) => (
          <button
            key={item.name}
            onClick={() => onSelect(item.name)}
            className={`rounded-md border px-3 py-2 text-left text-sm ${item.name === profile.name ? "border-emerald-400 bg-emerald-500/15 text-emerald-100" : "border-line bg-panelSoft text-slate-300 hover:border-slate-500"}`}
          >
            {item.name}
          </button>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-5 gap-2 text-xs">
        {Object.entries(profile.weights).map(([key, value]) => (
          <div key={key} className="rounded-md bg-command p-2">
            <p className="text-slate-400">{key}</p>
            <p className="font-semibold text-slate-100">{formatPercent(value)}</p>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}
