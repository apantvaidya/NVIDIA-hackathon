import { Bell, CalendarClock, Zap } from "lucide-react";
import { SectionCard } from "../layout/SectionCard";
import { StatusBadge } from "../layout/StatusBadge";

export function ActivityTimeline({ actions, events, alerts }: { actions: any[]; events: any[]; alerts: any[] }) {
  const items: any[] = [
    ...actions.map((item, index) => ({ id: `a-${index}`, type: "action", title: item.action_type, description: JSON.stringify(item.payload || {}).slice(0, 140), virtual_week: item.virtual_week, raw: item })),
    ...events.map((item, index) => ({ id: `e-${index}`, type: "event", title: item.event_type, description: item.message, virtual_week: item.virtual_week, raw: item })),
    ...alerts.map((item, index) => ({ id: `al-${index}`, type: "alert", title: item.type, description: item.message, virtual_week: item.virtual_week, severity: item.severity, raw: item })),
  ].sort((a, b) => (b.virtual_week ?? 0) - (a.virtual_week ?? 0)).slice(0, 18);

  const icon = (type: string) => type === "action" ? <Zap className="h-4 w-4" /> : type === "alert" ? <Bell className="h-4 w-4" /> : <CalendarClock className="h-4 w-4" />;

  return (
    <SectionCard title="Activity Timeline">
      {items.length === 0 ? <p className="text-sm text-slate-400">No activity yet.</p> : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className="flex gap-3">
              <div className="mt-1 text-slate-400">{icon(item.type)}</div>
              <div className="flex-1 rounded-md border border-line bg-command p-3">
                <div className="flex items-center justify-between gap-2"><strong className="text-sm">{item.title || item.type}</strong><StatusBadge status={item.severity || item.type} /></div>
                <p className="mt-1 text-sm text-slate-300">{item.description}</p>
                <p className="mt-1 text-xs text-slate-500">Week {item.virtual_week ?? "n/a"}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
