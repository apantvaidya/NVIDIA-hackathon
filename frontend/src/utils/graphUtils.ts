import type { AnyRecord, GraphResponse } from "../api/types";

export function normalizeGraph(graph?: GraphResponse, state?: AnyRecord): GraphResponse {
  if (graph?.nodes?.length && graph?.edges?.length) return graph;

  if (graph?.graph && graph?.lanes) {
    const nodeIds = new Set<string>();
    Object.entries(graph.graph).forEach(([source, targets]) => {
      nodeIds.add(source);
      (targets as string[]).forEach((target) => nodeIds.add(target));
    });
    return {
      nodes: Array.from(nodeIds).map((id) => ({ id, label: id, type: "legacy", status: "active" })),
      edges: Object.entries(graph.lanes).map(([id, lane]: [string, any]) => ({
        id,
        source: lane.origin,
        target: lane.destination,
        mode: lane.mode,
        status: lane.status,
        cost_per_unit: lane.cost_per_unit,
        transit_weeks: lane.transit_weeks ?? lane.transit_days,
        emissions_per_unit: lane.emissions_per_unit,
      })),
    };
  }

  if (state?.nodes) {
    return {
      nodes: Object.values(state.nodes).map((node: any) => ({
        id: node.node_id,
        label: node.name,
        type: node.node_type,
        tier: node.tier,
        status: node.status,
        metrics: node,
      })),
      edges: Object.entries(state.lanes || {}).map(([id, lane]: [string, any]) => ({
        id,
        source: lane.origin,
        target: lane.destination,
        mode: lane.mode,
        status: lane.status,
        cost_per_unit: lane.cost_per_unit,
        transit_weeks: lane.transit_weeks,
        emissions_per_unit: lane.emissions_per_unit,
      })),
    };
  }

  return {
    nodes: [
      "supplier_a",
      "supplier_b",
      "west_dc",
      "east_dc",
      "west_region",
      "east_region",
    ].map((id) => ({ id, label: id, type: "fallback", status: "active" })),
    edges: [
      { id: "supplier_a_west", source: "supplier_a", target: "west_dc" },
      { id: "supplier_b_west", source: "supplier_b", target: "west_dc" },
      { id: "west_region", source: "west_dc", target: "west_region" },
      { id: "west_east_truck", source: "west_dc", target: "east_dc", mode: "truck" },
      { id: "west_east_air", source: "west_dc", target: "east_dc", mode: "air" },
      { id: "east_region", source: "east_dc", target: "east_region" },
    ],
  };
}
