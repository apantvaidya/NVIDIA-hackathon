import type { AnyRecord } from "../../api/types";
import { formatCurrency, formatNumber, formatPercent } from "../../utils/formatters";
import {
  getAirFreightShare,
  getAverageServiceLevel,
  getAverageStockoutRisk,
  getEstimatedEmissions,
  getEstimatedProfit,
  getMaxWarehouseUtilization,
  getSupplierRiskIndex,
  getTransportCost,
} from "../../utils/kpiUtils";

const rows = [
  ["Profit", getEstimatedProfit, formatCurrency],
  ["Service Level", getAverageServiceLevel, (v?: number) => formatPercent(v, 1)],
  ["Stockout Risk", getAverageStockoutRisk, (v?: number) => formatPercent(v, 1)],
  ["Transport Cost", getTransportCost, formatCurrency],
  ["Emissions", getEstimatedEmissions, (v?: number) => formatNumber(v, 1)],
  ["Air Freight Share", getAirFreightShare, (v?: number) => formatPercent(v, 1)],
  ["Warehouse Utilization", getMaxWarehouseUtilization, (v?: number) => formatPercent(v, 1)],
  ["Supplier Risk", getSupplierRiskIndex, (v?: number) => formatPercent(v, 1)],
] as const;

export function BeforeAfterComparison({ before, after }: { before?: AnyRecord; after?: AnyRecord }) {
  return (
    <div className="overflow-hidden rounded-md border border-line">
      <table className="w-full text-left text-sm">
        <thead className="bg-command text-xs uppercase text-slate-400"><tr><th className="p-2">Metric</th><th className="p-2">Before</th><th className="p-2">After</th></tr></thead>
        <tbody>
          {rows.map(([label, getter, formatter]) => (
            <tr key={label} className="border-t border-line">
              <td className="p-2 text-slate-300">{label}</td>
              <td className="p-2">{formatter(getter(before))}</td>
              <td className="p-2">{formatter(getter(after))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
