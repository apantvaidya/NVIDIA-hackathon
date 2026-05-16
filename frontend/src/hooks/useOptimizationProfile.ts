import { useEffect, useMemo, useState } from "react";
import type { OptimizationProfile } from "../api/types";

export const PROFILES: OptimizationProfile[] = [
  { name: "Balanced", weights: { cost: 0.3, service: 0.3, emissions: 0.15, inventory: 0.15, risk: 0.1 }, hard_constraints: { min_service_level: 0.95, max_air_freight_share: 0.35, max_supplier_risk: 0.12, max_warehouse_utilization: 0.95 } },
  { name: "Cost Saver", weights: { cost: 0.5, service: 0.2, emissions: 0.1, inventory: 0.15, risk: 0.05 }, hard_constraints: { min_service_level: 0.92, max_air_freight_share: 0.2, max_supplier_risk: 0.16, max_warehouse_utilization: 0.95 } },
  { name: "Service First", weights: { cost: 0.15, service: 0.5, emissions: 0.08, inventory: 0.12, risk: 0.15 }, hard_constraints: { min_service_level: 0.98, max_air_freight_share: 0.5, max_supplier_risk: 0.12, max_warehouse_utilization: 0.95 } },
  { name: "Low Carbon", weights: { cost: 0.2, service: 0.25, emissions: 0.4, inventory: 0.1, risk: 0.05 }, hard_constraints: { min_service_level: 0.94, max_air_freight_share: 0.1, max_supplier_risk: 0.14, max_warehouse_utilization: 0.95 } },
  { name: "Resilience First", weights: { cost: 0.15, service: 0.3, emissions: 0.1, inventory: 0.15, risk: 0.3 }, hard_constraints: { min_service_level: 0.96, max_air_freight_share: 0.35, max_supplier_risk: 0.08, max_warehouse_utilization: 0.9 } },
  { name: "Custom", weights: { cost: 0.3, service: 0.3, emissions: 0.15, inventory: 0.15, risk: 0.1 }, hard_constraints: { min_service_level: 0.95, max_air_freight_share: 0.35, max_supplier_risk: 0.12, max_warehouse_utilization: 0.95 } },
];

const storageKey = "chainpilot.optimizationProfile";

export function useOptimizationProfile() {
  const [profile, setProfile] = useState<OptimizationProfile>(() => {
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return PROFILES[0];
      }
    }
    return PROFILES[0];
  });

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(profile));
  }, [profile]);

  const profileNames = useMemo(() => PROFILES.map((item) => item.name), []);
  const selectProfile = (name: string) => {
    const next = PROFILES.find((item) => item.name === name) || PROFILES[0];
    setProfile(next);
  };

  return { profile, setProfile, selectProfile, profileNames, profiles: PROFILES };
}
