import type { AgentEpisode, AgentTimelineResponse, AnyRecord } from "./types";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function requestJson<T = AnyRecord>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      detail = body.detail || body.message || JSON.stringify(body);
    } catch {
      detail = response.statusText;
    }
    throw new Error(`${path} failed (${response.status}): ${detail}`);
  }
  return response.json();
}

export const getState = () => requestJson("/state");
export const getKpis = () => requestJson("/kpis");
export const getGraph = () => requestJson("/graph");
export const getActionsHistory = () => requestJson<any[]>("/actions/history");
export const getEventsHistory = () => requestJson<any[]>("/events/history");
export const getAlertsHistory = () => requestJson<any[]>("/alerts/history");
export const getSimulationStatus = () => requestJson("/simulation/status");

export const startSimulation = () =>
  requestJson("/simulation/start", { method: "POST" });
export const stopSimulation = () =>
  requestJson("/simulation/stop", { method: "POST" });
export const tickSimulation = () => requestJson("/tick", { method: "POST" });
export const resetSimulation = () => requestJson("/reset", { method: "POST" });

export const createAgentEpisode = (body: AnyRecord) =>
  requestJson<AgentEpisode>("/api/agent/episodes", {
    method: "POST",
    body: JSON.stringify(body),
  });
export const listAgentEpisodes = () =>
  requestJson<AgentEpisode[]>("/api/agent/episodes");
export const getAgentEpisodeTimeline = (episodeId: string) =>
  requestJson<AgentTimelineResponse>(`/api/agent/episodes/${episodeId}/timeline`);
export const getAgentContext = (episodeId: string) =>
  requestJson(`/api/agent/episodes/${episodeId}/context`);
export const submitAgentEvent = (body: AnyRecord) =>
  requestJson("/api/agent/events", {
    method: "POST",
    body: JSON.stringify(body),
  });

export async function safeCall<T>(
  label: string,
  fn: () => Promise<T>,
): Promise<{ data?: T; error?: string }> {
  try {
    return { data: await fn() };
  } catch (error) {
    return {
      error: error instanceof Error ? `${label}: ${error.message}` : `${label}: failed`,
    };
  }
}
