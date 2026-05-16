import type { AnyRecord } from "../api/types";

const values = (record?: Record<string, number>) =>
  Object.values(record || {}).filter((value) => typeof value === "number");

const average = (items: number[]) =>
  items.length ? items.reduce((sum, item) => sum + item, 0) / items.length : undefined;

export const getEstimatedProfit = (kpis?: AnyRecord) =>
  kpis?.financial?.estimated_profit ?? kpis?.estimated_profit;

export const getAverageServiceLevel = (kpis?: AnyRecord) =>
  average(values(kpis?.service?.service_level_estimate));

export const getAverageStockoutRisk = (kpis?: AnyRecord) =>
  average(values(kpis?.service?.stockout_risk ?? kpis?.stockout_risk));

export const getTransportCost = (kpis?: AnyRecord) =>
  kpis?.financial?.transport_cost ?? kpis?.logistics?.estimated_transport_cost ?? kpis?.estimated_total_cost;

export const getEstimatedEmissions = (kpis?: AnyRecord) =>
  kpis?.logistics?.estimated_emissions ?? kpis?.estimated_emissions;

export const getAirFreightShare = (kpis?: AnyRecord) =>
  kpis?.logistics?.air_freight_share ?? 0;

export const getMaxWarehouseUtilization = (kpis?: AnyRecord) => {
  const items = values(kpis?.inventory?.warehouse_utilization);
  return items.length ? Math.max(...items) : undefined;
};

export const getSupplierRiskIndex = (kpis?: AnyRecord) =>
  kpis?.sourcing?.supplier_risk_index;

export const getFinancialPenalty = (kpis?: AnyRecord) =>
  (kpis?.financial?.stockout_penalty || 0) +
  (kpis?.financial?.vendor_compliance_fines || 0) +
  (kpis?.financial?.wastage_cost || 0);

export const sumNested = (record?: AnyRecord): number => {
  if (!record) return 0;
  return Object.values(record).reduce((sum, value) => {
    if (typeof value === "number") return sum + value;
    if (value && typeof value === "object") return sum + sumNested(value);
    return sum;
  }, 0);
};
