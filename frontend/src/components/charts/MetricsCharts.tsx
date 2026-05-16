import type { ReactElement } from "react";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { KpiSnapshot } from "../../api/types";
import { getAirFreightShare, getAverageServiceLevel, getAverageStockoutRisk, getEstimatedEmissions, getEstimatedProfit, getTransportCost } from "../../utils/kpiUtils";
import { SectionCard } from "../layout/SectionCard";

export function MetricsCharts({ history }: { history: KpiSnapshot[] }) {
  const data = history.map((item) => ({
    week: item.virtualWeek,
    profit: getEstimatedProfit(item.kpis) || 0,
    service: (getAverageServiceLevel(item.kpis) || 0) * 100,
    stockout: (getAverageStockoutRisk(item.kpis) || 0) * 100,
    transport: getTransportCost(item.kpis) || 0,
    emissions: getEstimatedEmissions(item.kpis) || 0,
    air: (getAirFreightShare(item.kpis) || 0) * 100,
  }));
  if (data.length < 2) return <SectionCard title="Metrics Charts"><p className="text-sm text-slate-400">Charts will populate after a few polling snapshots.</p></SectionCard>;
  return (
    <SectionCard title="Metrics Charts">
      <div className="grid gap-4 xl:grid-cols-2">
        <Chart title="Profit over time"><AreaChart data={data}><CartesianGrid stroke="#24384b" /><XAxis dataKey="week" /><YAxis /><Tooltip /><Area dataKey="profit" stroke="#34d399" fill="#34d39933" /></AreaChart></Chart>
        <Chart title="Service vs stockout"><LineChart data={data}><CartesianGrid stroke="#24384b" /><XAxis dataKey="week" /><YAxis /><Tooltip /><Line dataKey="service" stroke="#38bdf8" /><Line dataKey="stockout" stroke="#f87171" /></LineChart></Chart>
        <Chart title="Transport cost and emissions"><LineChart data={data}><CartesianGrid stroke="#24384b" /><XAxis dataKey="week" /><YAxis /><Tooltip /><Line dataKey="transport" stroke="#fbbf24" /><Line dataKey="emissions" stroke="#a78bfa" /></LineChart></Chart>
        <Chart title="Air freight share"><AreaChart data={data}><CartesianGrid stroke="#24384b" /><XAxis dataKey="week" /><YAxis /><Tooltip /><Area dataKey="air" stroke="#fb7185" fill="#fb718533" /></AreaChart></Chart>
      </div>
    </SectionCard>
  );
}

function Chart({ title, children }: { title: string; children: ReactElement }) {
  return <div className="h-64 rounded-md bg-command p-3"><p className="mb-2 text-sm text-slate-300">{title}</p><ResponsiveContainer width="100%" height="88%">{children}</ResponsiveContainer></div>;
}
