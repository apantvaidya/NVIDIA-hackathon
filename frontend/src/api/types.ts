export type AnyRecord = Record<string, any>;

export interface SimulationStatus {
  simulation_status?: "running" | "stopped" | string;
  status?: string;
  running?: boolean;
  virtual_week?: number;
  time_step?: number;
  [key: string]: any;
}

export interface GraphNode {
  id: string;
  label?: string;
  type?: string;
  tier?: number;
  status?: string;
  metrics?: AnyRecord;
  [key: string]: any;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  mode?: string;
  status?: string;
  cost_per_unit?: number;
  transit_weeks?: number;
  emissions_per_unit?: number;
  [key: string]: any;
}

export interface GraphResponse {
  nodes?: GraphNode[];
  edges?: GraphEdge[];
  graph?: AnyRecord;
  lanes?: AnyRecord;
  [key: string]: any;
}

export interface KpiSnapshot {
  timestamp: number;
  virtualWeek: number;
  kpis: AnyRecord;
}

export interface OptimizationProfile {
  name: string;
  weights: {
    cost: number;
    service: number;
    emissions: number;
    inventory: number;
    risk: number;
  };
  hard_constraints: {
    min_service_level: number;
    max_air_freight_share: number;
    max_supplier_risk: number;
    max_warehouse_utilization: number;
  };
}

export interface AgentEpisode {
  id: string;
  simulation_id?: string;
  status?: string;
  trigger?: AnyRecord;
  user_preferences?: AnyRecord;
  created_at?: string;
  updated_at?: string;
  [key: string]: any;
}

export interface AgentEvent {
  id: string;
  episode_id: string;
  agent_id: string;
  event_type: string;
  title: string;
  summary: string;
  payload?: AnyRecord;
  target_event_id?: string | null;
  created_at?: string;
  [key: string]: any;
}

export interface AgentTimelineResponse {
  episode?: AgentEpisode;
  events?: AgentEvent[];
}
