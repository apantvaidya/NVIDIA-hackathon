import type { NodeProps } from "@xyflow/react";
import { Handle, Position } from "@xyflow/react";
import { Factory, Package, ShoppingCart, Truck } from "lucide-react";
import type { ReactElement } from "react";
import { formatPercent, titleize } from "../../utils/formatters";

const icons: Record<string, ReactElement> = {
  sourcing: <Package className="h-4 w-4" />,
  production: <Factory className="h-4 w-4" />,
  distribution: <Truck className="h-4 w-4" />,
  demand_channel: <ShoppingCart className="h-4 w-4" />,
};

export function CustomSupplyNode({ data }: NodeProps) {
  const node: any = data;
  const status = node.status || "active";
  const critical = node.metrics?.stockout_risk > 0.2 || node.metrics?.utilization > 0.95;
  const warning = node.metrics?.utilization > 0.9 || status !== "active";
  const border = critical ? "border-red-400" : warning ? "border-amber-400" : "border-emerald-400/70";
  return (
    <div className={`min-w-44 rounded-lg border ${border} bg-[#101923] p-3 text-slate-100 shadow-lg`}>
      <Handle type="target" position={Position.Left} className="!bg-slate-400" />
      <div className="flex items-center gap-2">
        <span className="text-emerald-300">{icons[node.type] || <Package className="h-4 w-4" />}</span>
        <strong className="text-sm">{node.label}</strong>
      </div>
      <p className="mt-1 text-xs text-slate-400">{titleize(node.type)} · Tier {node.tier ?? "n/a"}</p>
      {node.metrics?.utilization !== undefined && <p className="mt-2 text-xs">Utilization {formatPercent(node.metrics.utilization, 1)}</p>}
      {node.metrics?.active_product_id && <p className="mt-2 text-xs">Active {titleize(node.metrics.active_product_id)}</p>}
      {node.metrics?.stockout_risk !== undefined && <p className="mt-2 text-xs">Risk {formatPercent(node.metrics.stockout_risk, 1)}</p>}
      <Handle type="source" position={Position.Right} className="!bg-slate-400" />
    </div>
  );
}
