import type { AgentEvent } from "../api/types";
import { AgentEventCard } from "./AgentEventCard";

export function AgentTimeline({ events }: { events: AgentEvent[] }) {
  if (!events.length) {
    return (
      <div className="rounded-lg border border-line bg-command p-4 text-sm text-slate-400">
        No agent events yet. Create an episode, then have Red submit RED_PLAN to begin the decision cycle.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {events.map((event) => <AgentEventCard key={event.id} event={event} />)}
    </div>
  );
}
