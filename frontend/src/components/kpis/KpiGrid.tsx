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
import { SectionCard } from "../layout/SectionCard";
import { KpiCard } from "./KpiCard";

const delta = (current?: number, previous?: number) =>
  typeof current === "number" && typeof previous === "number" ? current - previous : undefined;

export function KpiGrid({ kpis, previousKpis }: { kpis?: AnyRecord; previousKpis?: AnyRecord }) {
  const profit = getEstimatedProfit(kpis);
  const service = getAverageServiceLevel(kpis);
  const stockout = getAverageStockoutRisk(kpis);
  const transport = getTransportCost(kpis);
  const emissions = getEstimatedEmissions(kpis);
  const air = getAirFreightShare(kpis);
  const utilization = getMaxWarehouseUtilization(kpis);
  const risk = getSupplierRiskIndex(kpis);

  return (
    <SectionCard title="KPI Cards">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard title="Estimated Profit" value={formatCurrency(profit)} previous={delta(profit, getEstimatedProfit(previousKpis))} status={(profit ?? 0) < 5000 ? "critical" : "healthy"} />
        <KpiCard title="Service Level" value={formatPercent(service, 1)} previous={delta(service, getAverageServiceLevel(previousKpis))} status={(service ?? 1) < 0.92 ? "critical" : (service ?? 1) < 0.96 ? "warning" : "healthy"} />
        <KpiCard title="Stockout Risk" value={formatPercent(stockout, 1)} previous={delta(stockout, getAverageStockoutRisk(previousKpis))} status={(stockout ?? 0) > 0.2 ? "critical" : (stockout ?? 0) > 0.1 ? "warning" : "healthy"} />
        <KpiCard title="Transport Cost" value={formatCurrency(transport)} previous={delta(transport, getTransportCost(previousKpis))} />
        <KpiCard title="Emissions" value={formatNumber(emissions, 1)} previous={delta(emissions, getEstimatedEmissions(previousKpis))} status={(emissions ?? 0) > 1200 ? "warning" : "healthy"} />
        <KpiCard title="Air Freight Share" value={formatPercent(air, 1)} previous={delta(air, getAirFreightShare(previousKpis))} status={(air ?? 0) > 0.35 ? "warning" : "healthy"} />
        <KpiCard title="Warehouse Utilization" value={formatPercent(utilization, 1)} previous={delta(utilization, getMaxWarehouseUtilization(previousKpis))} status={(utilization ?? 0) > 0.95 ? "critical" : (utilization ?? 0) > 0.9 ? "warning" : "healthy"} />
        <KpiCard title="Supplier Risk" value={formatPercent(risk, 1)} previous={delta(risk, getSupplierRiskIndex(previousKpis))} status={(risk ?? 0) > 0.12 ? "critical" : (risk ?? 0) > 0.08 ? "warning" : "healthy"} />
      </div>
    </SectionCard>
  );
}
