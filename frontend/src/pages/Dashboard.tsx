import { useState } from "react";
import { DashboardTabs, type DashboardView } from "../components/DashboardTabs";
import { SectionCard } from "../components/layout/SectionCard";
import { AppShell } from "../components/layout/AppShell";
import { AgentDecisionsView } from "../components/views/AgentDecisionsView";
import { ImpactAnalyticsView } from "../components/views/ImpactAnalyticsView";
import { OperationsView } from "../components/views/OperationsView";
import { useOptimizationProfile } from "../hooks/useOptimizationProfile";
import { useSimulationData } from "../hooks/useSimulationData";

export function Dashboard() {
  const initialView = typeof window === "undefined"
    ? "operations"
    : window.location.hash.replace("#", "");
  const [activeView, setActiveView] = useState<DashboardView>(
    ["operations", "agents", "analytics"].includes(initialView)
      ? (initialView as DashboardView)
      : "operations",
  );
  const changeView = (view: DashboardView) => {
    setActiveView(view);
    window.history.replaceState(null, "", `#${view}`);
  };
  const data = useSimulationData();
  const { profile, selectProfile } = useOptimizationProfile();
  const lastUpdated = data.kpiHistory[data.kpiHistory.length - 1]?.timestamp;

  return (
    <AppShell
      status={data.status}
      virtualWeek={data.kpis?.virtual_week ?? data.state?.virtual_week}
      profileName={profile.name}
      connectionHealthy={!data.error}
      lastUpdated={lastUpdated}
    >
      {data.error && (
        <div className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-100">
          Some endpoints failed, rendering available data: {data.error}
        </div>
      )}
      {data.loading && (
        <div className="mb-4 rounded-lg border border-line bg-panel p-3 text-sm text-slate-300">
          Loading simulation telemetry...
        </div>
      )}

      <DashboardTabs activeView={activeView} onChange={changeView} />

      {activeView === "operations" && (
        <OperationsView data={data} profile={profile} selectProfile={selectProfile} />
      )}
      {activeView === "agents" && <AgentDecisionsView actions={data.actions} />}
      {activeView === "analytics" && (
        <ImpactAnalyticsView
          kpiHistory={data.kpiHistory}
          actions={data.actions}
          alerts={data.alerts}
        />
      )}

      <div className="mt-5">
        <SectionCard title="Backend Connection">
          <p className="text-sm text-slate-400">
            Polling every 3 seconds. Missing fields are treated defensively so the frontend can survive backend evolution during the hackathon.
          </p>
        </SectionCard>
      </div>
    </AppShell>
  );
}
