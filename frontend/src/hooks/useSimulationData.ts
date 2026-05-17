import { useCallback, useEffect, useRef, useState } from "react";
import {
  getActionsHistory,
  getAlertsHistory,
  getEventsHistory,
  getGraph,
  getKpis,
  getSimulationStatus,
  getState,
  safeCall,
} from "../api/client";
import { connectRealtime } from "../api/realtime";
import type { AnyRecord, GraphResponse, KpiSnapshot, SimulationStatus } from "../api/types";

export function useSimulationData() {
  const [state, setState] = useState<AnyRecord>();
  const [kpis, setKpis] = useState<AnyRecord>();
  const [previousKpis, setPreviousKpis] = useState<AnyRecord>();
  const [graph, setGraph] = useState<GraphResponse>();
  const [actions, setActions] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [status, setStatus] = useState<SimulationStatus>();
  const [kpiHistory, setKpiHistory] = useState<KpiSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const latestKpis = useRef<AnyRecord>();

  const refresh = useCallback(async () => {
    const results = await Promise.all([
      safeCall("state", getState),
      safeCall("kpis", getKpis),
      safeCall("graph", getGraph),
      safeCall("actions", getActionsHistory),
      safeCall("events", getEventsHistory),
      safeCall("alerts", getAlertsHistory),
      safeCall("status", getSimulationStatus),
    ]);

    const [stateResult, kpisResult, graphResult, actionsResult, eventsResult, alertsResult, statusResult] = results;
    if (stateResult.data) setState(stateResult.data);
    if (kpisResult.data) {
      const kpiData = kpisResult.data;
      setPreviousKpis(latestKpis.current);
      latestKpis.current = kpiData;
      setKpis(kpiData);
      setKpiHistory((history) => [
        ...history.slice(-39),
        {
          timestamp: Date.now(),
          virtualWeek: kpiData.virtual_week ?? stateResult.data?.virtual_week ?? history.length,
          kpis: kpiData,
        },
      ]);
    }
    if (graphResult.data) setGraph(graphResult.data);
    if (actionsResult.data) setActions(Array.isArray(actionsResult.data) ? actionsResult.data : []);
    if (eventsResult.data) setEvents(Array.isArray(eventsResult.data) ? eventsResult.data : []);
    if (alertsResult.data) setAlerts(Array.isArray(alertsResult.data) ? alertsResult.data : []);
    if (statusResult.data) setStatus(statusResult.data);

    const errors = results.map((result) => result.error).filter(Boolean);
    setError(errors.length ? errors.join(" | ") : undefined);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const interval = window.setInterval(refresh, 3000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    const dispose = connectRealtime((message) => {
      if (
        message.type === "execution_applied" ||
        message.type === "state_updated" ||
        message.type === "agent_event" ||
        message.type === "episode_completed" ||
        message.type === "agent_state_reset"
      ) {
        refresh();
      }
    });
    return dispose;
  }, [refresh]);

  return { state, kpis, previousKpis, graph, actions, events, alerts, status, kpiHistory, loading, error, refresh };
}
