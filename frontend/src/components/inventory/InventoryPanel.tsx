import type { AnyRecord } from "../../api/types";
import { formatNumber, formatPercent, titleize } from "../../utils/formatters";
import { SectionCard } from "../layout/SectionCard";

function totalUnits(buckets: any[] = []) {
  return buckets.reduce((sum, bucket) => sum + (bucket.units || 0), 0);
}

export function InventoryPanel({ state, kpis }: { state?: AnyRecord; kpis?: AnyRecord }) {
  const nodeEntries = Object.entries(state?.nodes || state?.warehouses || {}).filter(([, node]: [string, any]) => node.inventory);
  return (
    <SectionCard title="Inventory">
      <div className="grid gap-3 md:grid-cols-2">
        {nodeEntries.map(([nodeId, node]: [string, any]) => (
          <div key={nodeId} className="rounded-md border border-line bg-command p-3">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-medium">{titleize(node.name || nodeId)}</h3>
              <span className="text-xs text-slate-400">{formatPercent(kpis?.inventory?.warehouse_utilization?.[nodeId], 1)} used</span>
            </div>
            <div className="mt-3 space-y-2">
              {Object.entries(node.inventory || {}).map(([productId, buckets]: [string, any]) => (
                <div key={productId} className="rounded bg-panelSoft p-2 text-sm">
                  <div className="flex justify-between"><span>{titleize(productId)}</span><strong>{formatNumber(totalUnits(buckets))} units</strong></div>
                  <p className="mt-1 text-xs text-slate-400">{Array.isArray(buckets) ? buckets.map((b) => `${b.units}@${b.age_weeks}w`).join(" · ") : "flat inventory"}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}
