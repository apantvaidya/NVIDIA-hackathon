import type { AnyRecord } from "../../api/types";
import { SectionCard } from "../layout/SectionCard";
import { StatusBadge } from "../layout/StatusBadge";

export function AlertsPanel({ kpis, alerts }: { kpis?: AnyRecord; alerts: any[] }) {
  const combined = [...(kpis?.alerts || []), ...alerts].slice(-12).reverse();
  return (
    <SectionCard title="Alerts">
      {combined.length === 0 ? <p className="text-sm text-slate-400">No active alerts.</p> : (
        <div className="space-y-2">
          {combined.map((alert, index) => (
            <div key={`${alert.type}-${index}`} className="rounded-md border border-line bg-command p-3">
              <div className="flex items-center justify-between gap-2"><strong className="text-sm">{alert.type || "alert"}</strong><StatusBadge status={alert.severity || "warning"} /></div>
              <p className="mt-1 text-sm text-slate-300">{alert.message}</p>
              {alert.virtual_week !== undefined && <p className="mt-1 text-xs text-slate-500">Week {alert.virtual_week}</p>}
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
