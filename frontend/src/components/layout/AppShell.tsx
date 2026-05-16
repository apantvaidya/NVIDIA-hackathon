import type { ReactNode } from "react";
import { Activity, RadioTower } from "lucide-react";
import type { OptimizationProfile, SimulationStatus } from "../../api/types";
import { StatusBadge } from "./StatusBadge";

export function AppShell({ children, status, virtualWeek, profileName }: { children: ReactNode; status?: SimulationStatus; virtualWeek?: number; profileName: string }) {
  const simStatus = status?.simulation_status || status?.status || (status?.running ? "running" : "stopped");
  return (
    <div className="min-h-screen bg-command text-slate-100">
      <div className="border-b border-line bg-[#0d1722]/95">
        <div className="mx-auto flex max-w-[1800px] flex-wrap items-center justify-between gap-3 px-5 py-4">
          <div>
            <div className="flex items-center gap-3">
              <RadioTower className="h-7 w-7 text-emerald-300" />
              <h1 className="text-2xl font-semibold tracking-tight">ChainPilot</h1>
            </div>
            <p className="mt-1 text-sm text-slate-400">Autonomous Supply Chain Simulation</p>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span className="rounded-md border border-line bg-panelSoft px-3 py-2">Virtual week <strong>{virtualWeek ?? status?.virtual_week ?? 0}</strong></span>
            <StatusBadge status={simStatus} />
            <span className="rounded-md border border-line bg-panelSoft px-3 py-2">Profile <strong>{profileName}</strong></span>
            <Activity className="h-5 w-5 text-slate-400" />
          </div>
        </div>
      </div>
      <main className="mx-auto max-w-[1800px] px-5 py-5">{children}</main>
    </div>
  );
}
