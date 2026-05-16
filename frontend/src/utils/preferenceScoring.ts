import type { AnyRecord, OptimizationProfile } from "../api/types";
import {
  getAirFreightShare,
  getAverageServiceLevel,
  getAverageStockoutRisk,
  getEstimatedEmissions,
  getEstimatedProfit,
  getFinancialPenalty,
  getMaxWarehouseUtilization,
  getSupplierRiskIndex,
  getTransportCost,
  sumNested,
} from "./kpiUtils";

const clamp = (value: number) => Math.max(0, Math.min(100, value));
const neutral = (value?: number) => (typeof value === "number" && Number.isFinite(value) ? value : 70);

export function scoreCost(kpis?: AnyRecord): number {
  const profit = getEstimatedProfit(kpis);
  const transport = getTransportCost(kpis) || 0;
  const penalty = getFinancialPenalty(kpis);
  if (typeof profit !== "number") return 70;
  return clamp(70 + profit / 700 - transport / 120 - penalty / 120);
}

export function scoreService(kpis?: AnyRecord): number {
  const service = getAverageServiceLevel(kpis);
  const risk = getAverageStockoutRisk(kpis) || 0;
  const unmet = sumNested(kpis?.service?.unmet_demand_units);
  if (typeof service !== "number") return 70;
  return clamp(service * 100 - risk * 35 - unmet / 120);
}

export function scoreEmissions(kpis?: AnyRecord): number {
  const emissions = getEstimatedEmissions(kpis);
  const air = getAirFreightShare(kpis) || 0;
  if (typeof emissions !== "number") return 70;
  return clamp(100 - emissions / 18 - air * 35);
}

export function scoreInventory(kpis?: AnyRecord): number {
  const utilization = getMaxWarehouseUtilization(kpis);
  const nearExpiration = sumNested(kpis?.inventory?.units_near_expiration);
  const excess = sumNested(kpis?.inventory?.excess_inventory);
  if (typeof utilization !== "number") return 70;
  return clamp(100 - Math.max(0, utilization - 0.82) * 180 - nearExpiration / 60 - excess / 400);
}

export function scoreRisk(kpis?: AnyRecord): number {
  const supplierRisk = getSupplierRiskIndex(kpis);
  const uncertainty = kpis?.sourcing?.lead_time_uncertainty_index;
  if (typeof supplierRisk !== "number") return 70;
  return clamp(100 - supplierRisk * 420 - neutral(uncertainty) * 20);
}

export function calculatePreferenceFit(kpis: AnyRecord | undefined, profile: OptimizationProfile) {
  const scores = {
    cost: scoreCost(kpis),
    service: scoreService(kpis),
    emissions: scoreEmissions(kpis),
    inventory: scoreInventory(kpis),
    risk: scoreRisk(kpis),
  };
  const overall =
    scores.cost * profile.weights.cost +
    scores.service * profile.weights.service +
    scores.emissions * profile.weights.emissions +
    scores.inventory * profile.weights.inventory +
    scores.risk * profile.weights.risk;
  return { overall: Math.round(clamp(overall)), scores };
}
