import { titleize } from "../../utils/formatters";

const classes: Record<string, string> = {
  healthy: "border-emerald-400/40 bg-emerald-500/15 text-emerald-200",
  active: "border-emerald-400/40 bg-emerald-500/15 text-emerald-200",
  running: "border-emerald-400/40 bg-emerald-500/15 text-emerald-200",
  warning: "border-amber-400/40 bg-amber-500/15 text-amber-200",
  standby: "border-sky-400/40 bg-sky-500/15 text-sky-200",
  critical: "border-red-400/40 bg-red-500/15 text-red-200",
  stopped: "border-slate-400/30 bg-slate-500/15 text-slate-300",
};

export function StatusBadge({ status = "unknown" }: { status?: string }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${classes[status] || classes.stopped}`}>
      {titleize(status)}
    </span>
  );
}
