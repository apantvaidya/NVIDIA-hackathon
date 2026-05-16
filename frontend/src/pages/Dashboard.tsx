import { AlertsPanel } from "../components/alerts/AlertsPanel";
import { AgentDecisionConsole } from "../components/AgentDecisionConsole";
import { MetricsCharts } from "../components/charts/MetricsCharts";
import { OptimizationPreferences } from "../components/controls/OptimizationPreferences";
import { SimulationControls } from "../components/controls/SimulationControls";
import { SupplyChainGraph } from "../components/graph/SupplyChainGraph";
import { DecisionImpactPanel } from "../components/impact/DecisionImpactPanel";
import { InTransitPanel } from "../components/inventory/InTransitPanel";
import { InventoryPanel } from "../components/inventory/InventoryPanel";
import { KpiGrid } from "../components/kpis/KpiGrid";
import { PreferenceFitScore } from "../components/kpis/PreferenceFitScore";
import { AppShell } from "../components/layout/AppShell";
import { SectionCard } from "../components/layout/SectionCard";
import { ActivityTimeline } from "../components/timeline/ActivityTimeline";
import { useOptimizationProfile } from "../hooks/useOptimizationProfile";
import { useSimulationData } from "../hooks/useSimulationData";

export function Dashboard() {
  const data = useSimulationData();
  const { profile, selectProfile } = useOptimizationProfile();

  return (
    <AppShell status={data.status} virtualWeek={data.kpis?.virtual_week ?? data.state?.virtual_week} profileName={profile.name}>
      {data.error && (
        <div className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-100">
          Some endpoints failed, rendering available data: {data.error}
        </div>
      )}
      {data.loading && <div className="mb-4 rounded-lg border border-line bg-panel p-3 text-sm text-slate-300">Loading simulation telemetry...</div>}

      <div className="grid gap-4 xl:grid-cols-12">
        <div className="space-y-4 xl:col-span-8">
          <SimulationControls refresh={data.refresh} />
          <SupplyChainGraph graph={data.graph} state={data.state} />
          <KpiGrid kpis={data.kpis} previousKpis={data.previousKpis} />
          <MetricsCharts history={data.kpiHistory} />
        </div>

        <div className="space-y-4 xl:col-span-4">
          <OptimizationPreferences profile={profile} onSelect={selectProfile} />
          <PreferenceFitScore kpis={data.kpis} profile={profile} />
          <AlertsPanel kpis={data.kpis} alerts={data.alerts} />
        </div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <InventoryPanel state={data.state} kpis={data.kpis} />
        <InTransitPanel state={data.state} />
        <ActivityTimeline actions={data.actions} events={data.events} alerts={data.alerts} />
      </div>

      <div className="mt-4">
        <AgentDecisionConsole />
      </div>

      <div className="mt-4">
        <DecisionImpactPanel actions={data.actions} />
      </div>

      <div className="mt-4">
        <SectionCard title="Backend Connection">
          <p className="text-sm text-slate-400">Polling every 3 seconds. Missing fields are treated defensively so the frontend can survive backend evolution during the hackathon.</p>
        </SectionCard>
      </div>
    </AppShell>
  );
}
