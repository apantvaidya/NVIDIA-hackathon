import type { AnyRecord } from "../../api/types";
import { titleize } from "../../utils/formatters";
import { SectionCard } from "../layout/SectionCard";
import { StatusBadge } from "../layout/StatusBadge";

export function InTransitPanel({ state }: { state?: AnyRecord }) {
  const shipments = state?.in_transit_shipments || [];
  return (
    <SectionCard title="In-Transit Shipments">
      {shipments.length === 0 ? <p className="text-sm text-slate-400">No active shipments.</p> : (
        <div className="space-y-2">
          {shipments.map((shipment: any) => (
            <div key={shipment.shipment_id} className="rounded-md border border-line bg-command p-3 text-sm">
              <div className="flex items-center justify-between"><strong>{titleize(shipment.product_id)}</strong><StatusBadge status={shipment.mode} /></div>
              <p className="mt-1 text-slate-300">{shipment.units} units · {shipment.from_node || shipment.from} → {shipment.to_node || shipment.to}</p>
              <p className="mt-1 text-xs text-slate-500">Created week {shipment.created_week}, arrival week {shipment.arrival_week}</p>
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
