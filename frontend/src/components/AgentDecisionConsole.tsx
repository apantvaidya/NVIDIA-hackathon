import { useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { createAgentEpisode } from "../api/client";
import { useAgentData } from "../hooks/useAgentData";
import { titleize } from "../utils/formatters";
import { SectionCard } from "./layout/SectionCard";
import { StatusBadge } from "./layout/StatusBadge";
import { AgentTimeline } from "./AgentTimeline";

export function AgentDecisionConsole() {
  const agentData = useAgentData();
  const [creating, setCreating] = useState(false);
  const selectedEpisode = useMemo(
    () => agentData.episodes.find((episode) => episode.id === agentData.selectedEpisodeId),
    [agentData.episodes, agentData.selectedEpisodeId],
  );

  async function createManualEpisode() {
    setCreating(true);
    try {
      const episode = await createAgentEpisode({
        simulation_id: "default",
        trigger: { type: "manual", summary: "Manual agent review requested from dashboard." },
        user_preferences: {
          profile: "balanced",
          weights: { profit: 0.25, service: 0.35, cost: 0.25, emissions: 0.15 },
        },
      });
      agentData.setSelectedEpisodeId(episode.id);
      await agentData.refresh();
    } finally {
      setCreating(false);
    }
  }

  return (
    <SectionCard title="Agent Decision Console" subtitle="Flow: Red writes the initial plan, Blue critiques and revises it into the final plan, then Executor-Narrator executes and explains what happened.">
      <div className="mb-4 grid gap-3 lg:grid-cols-[1fr_auto]">
        <div className="rounded-lg border border-line bg-command p-3">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm text-slate-400" htmlFor="episode-select">Active Episode</label>
            <select
              id="episode-select"
              className="min-w-64 rounded-md border border-line bg-panelSoft px-3 py-2 text-sm text-slate-100"
              value={agentData.selectedEpisodeId || ""}
              onChange={(event) => agentData.setSelectedEpisodeId(event.target.value)}
            >
              <option value="">No episode selected</option>
              {agentData.episodes.map((episode) => (
                <option key={episode.id} value={episode.id}>
                  {episode.id} · {episode.trigger?.summary || episode.status}
                </option>
              ))}
            </select>
            {selectedEpisode && <StatusBadge status={selectedEpisode.status || "active"} />}
          </div>
          {selectedEpisode && (
            <div className="mt-3 grid gap-2 text-sm text-slate-300 md:grid-cols-3">
              <p><span className="text-slate-500">Problem:</span> {selectedEpisode.trigger?.summary || "No trigger summary"}</p>
              <p><span className="text-slate-500">Preference:</span> {titleize(selectedEpisode.user_preferences?.profile)}</p>
              <p><span className="text-slate-500">Created:</span> {selectedEpisode.created_at ? new Date(selectedEpisode.created_at).toLocaleString() : "n/a"}</p>
            </div>
          )}
        </div>
        <button
          onClick={createManualEpisode}
          disabled={creating}
          className="inline-flex items-center justify-center gap-2 rounded-md border border-emerald-400/50 bg-emerald-500/15 px-4 py-2 text-sm font-medium text-emerald-100 hover:bg-emerald-500/25 disabled:opacity-60"
        >
          <Plus className="h-4 w-4" /> New Episode
        </button>
      </div>

      {agentData.error && <p className="mb-3 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-100">{agentData.error}</p>}
      <div className="mb-4 grid gap-2 text-xs text-slate-400 md:grid-cols-5">
        {["RED_PLAN", "BLUE_ASSESSMENT", "BLUE_REVISED_PLAN", "EXECUTOR_ACTION", "NARRATION"].map((step) => (
          <div key={step} className="rounded-md border border-line bg-command p-2 text-center">{step}</div>
        ))}
      </div>
      {agentData.loading ? <p className="text-sm text-slate-400">Loading agent timeline...</p> : <AgentTimeline events={agentData.timelineEvents} />}
    </SectionCard>
  );
}
