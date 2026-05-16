"""Blue Agent runner — validates and revises Red's plans.

Polls the backend every POLL_INTERVAL seconds for episodes in status
`waiting_for_blue_revised_plan`. For each one:
  1. Fetches full context (state + Red's plan).
  2. Calls openclaw `blue-agent` for [BLUE_ASSESSMENT, BLUE_REVISED_PLAN].
  3. POSTs both events.
"""

import os
import time
import traceback

from agent_common import (
    AGENT_RUN_ONCE, BACKEND, TARGET_EPISODE_ID, call_openclaw,
    episodes_with_status, get, log, normalize_transfer_request, post_event,
    timeline_events,
)

POLL_INTERVAL = int(os.environ.get("BLUE_POLL_INTERVAL", "2"))
OPENCLAW_AGENT = os.environ.get("BLUE_OPENCLAW_AGENT", "blue-agent")


def compact_state(state):
    """Keep OpenClaw context small enough to avoid timeout/context overflow."""
    if not state:
        return {}
    nodes = state.get("nodes") or {}
    lanes = state.get("lanes") or {}
    demand_channels = state.get("demand_channels") or {}
    distribution = {
        node_id: {
            "inventory_units": {
                product_id: sum(bucket.get("units", 0) for bucket in buckets)
                for product_id, buckets in (node.get("inventory") or {}).items()
            },
            "capacity_cubic_meters": node.get("capacity_cubic_meters"),
            "service_channels": node.get("service_channels"),
        }
        for node_id, node in nodes.items()
        if node.get("node_type") == "distribution"
    }
    return {
        "time_step": state.get("time_step"),
        "virtual_week": state.get("virtual_week"),
        "simulation_status": state.get("simulation_status"),
        "product_ids": list((state.get("products") or {}).keys()),
        "distribution": distribution,
        "demand": {
            channel_id: {
                "current_weekly_demand": channel.get("current_weekly_demand"),
                "served_by": channel.get("served_by"),
                "priority": channel.get("priority"),
            }
            for channel_id, channel in demand_channels.items()
        },
        "active_lanes": [
            {
                "lane_id": lane_id,
                "origin": lane.get("origin"),
                "destination": lane.get("destination"),
                "mode": lane.get("mode"),
                "transit_weeks": lane.get("transit_weeks"),
                "cost_per_unit": lane.get("cost_per_unit"),
                "status": lane.get("status"),
            }
            for lane_id, lane in lanes.items()
            if lane.get("status") == "active"
        ],
        "in_transit_count": len(state.get("in_transit_shipments", [])),
        "constraints": state.get("constraints", {}),
    }


def compact_kpis(kpis):
    if not kpis:
        return {}
    return {
        "virtual_week": kpis.get("virtual_week"),
        "estimated_profit": kpis.get("financial", {}).get("estimated_profit"),
        "transport_cost": kpis.get("financial", {}).get("transport_cost"),
        "stockout_penalty": kpis.get("financial", {}).get("stockout_penalty"),
        "vendor_compliance_fines": kpis.get("financial", {}).get("vendor_compliance_fines"),
        "stockout_risk": kpis.get("service", {}).get("stockout_risk"),
        "service_level": kpis.get("service", {}).get("service_level_estimate"),
        "unmet_demand": kpis.get("service", {}).get("unmet_demand_units"),
        "warehouse_utilization": kpis.get("inventory", {}).get("warehouse_utilization"),
        "air_freight_share": kpis.get("logistics", {}).get("air_freight_share"),
        "supplier_risk_index": kpis.get("sourcing", {}).get("supplier_risk_index"),
        "alerts": kpis.get("alerts", []),
    }


def normalize_blue_events(events, red_plan_payload):
    """Accept OpenClaw's plain assessment JSON and wrap it as backend events."""
    if isinstance(events, dict):
        if "events" in events and isinstance(events["events"], list):
            events = events["events"]
        elif "event_type" in events:
            events = [events]
        else:
            assessment_payload = {
                "decision": events.get("decision", "approved"),
                "approved": events.get("approved", events.get("decision") != "rejected"),
                "risk_level": events.get("risk_level", "medium"),
                "risks_identified": events.get("risks_identified", events.get("risks", [])),
                "constraint_violations": events.get("constraint_violations", []),
                "simulation_evidence": events.get("simulation_evidence", {}),
                "what_blue_changed": events.get("what_blue_changed", events.get("changes", [])),
                "confidence": events.get("confidence"),
            }
            revised_payload = (
                events.get("blue_revised_plan")
                or events.get("revised_plan")
                or events.get("final_action")
                or events.get("payload")
                or red_plan_payload
            )
            if isinstance(revised_payload, dict):
                revised_payload = normalize_transfer_request(revised_payload)
            events = [
                {
                    "event_type": "BLUE_ASSESSMENT",
                    "title": events.get("title", "Blue Agent Assessment"),
                    "summary": events.get("summary", "Blue assessed Red's plan."),
                    "payload": assessment_payload,
                }
            ]
            if assessment_payload["decision"] != "rejected":
                events.append({
                    "event_type": "BLUE_REVISED_PLAN",
                    "title": "Blue Agent Revised Final Plan",
                    "summary": "Blue approved or revised the final action for Executor-Narrator.",
                    "payload": revised_payload,
                })
    if not isinstance(events, list):
        raise ValueError(f"Blue output must be a JSON list or object. Got {type(events).__name__}: {repr(events)[:500]}")
    normalized = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if "event_type" not in event:
            event = {
                "event_type": "BLUE_ASSESSMENT",
                "title": event.get("title", "Blue Agent Assessment"),
                "summary": event.get("summary", "Blue assessed Red's plan."),
                "payload": event,
            }
        elif event.get("event_type") in {"BLUE_REVISED_PLAN", "FINAL_ACTION"} and isinstance(event.get("payload"), dict):
            event["payload"] = normalize_transfer_request(event["payload"])
        normalized.append(event)
    if not normalized:
        raise ValueError(f"Blue returned no usable events: {repr(events)[:500]}")
    return normalized


def next_episode_for_blue():
    if TARGET_EPISODE_ID:
        episode = get(f"/api/agent/episodes/{TARGET_EPISODE_ID}")
        if episode.get("status") != "waiting_for_blue_revised_plan":
            log(f"waiting: target episode {TARGET_EPISODE_ID} is {episode.get('status')}")
            return None
        return episode
    pending = episodes_with_status("waiting_for_blue_revised_plan")
    return pending[0] if pending else None


def _episode_has_blue_final(episode_id):
    return any(
        event.get("event_type") in {"BLUE_REVISED_PLAN", "FINAL_ACTION"}
        for event in timeline_events(episode_id)
    )


def step():
    episode = next_episode_for_blue()
    if not episode:
        return False
    episode_id = episode["id"]
    if _episode_has_blue_final(episode_id):
        log(f"waiting: episode {episode_id} already has a Blue final plan")
        return False
    ctx = get(f"/api/agent/episodes/{episode_id}/context")
    red_plan = next(
        (e for e in reversed(ctx.get("prior_agent_events", [])) if e.get("event_type") == "RED_PLAN"),
        None,
    )
    if not red_plan:
        log(f"waiting: episode {episode_id} has no RED_PLAN yet")
        return False
    message = {
        "red_plan": red_plan["payload"] if red_plan else None,
        "current_state": compact_state(ctx.get("current_state")),
        "current_kpis": compact_kpis(ctx.get("current_kpis")),
        "recent_alerts": (ctx.get("recent_alerts") or [])[-5:],
        "user_preferences": ctx.get("user_preferences"),
        "available_action_endpoints": ctx.get("available_action_endpoints"),
    }
    events = normalize_blue_events(
        call_openclaw(OPENCLAW_AGENT, message, prompt_name="blue_agent"),
        red_plan["payload"] if red_plan else {},
    )
    for event in events:
        post_event(
            episode_id,
            event["event_type"],
            event.get("title", event["event_type"]),
            event.get("summary", ""),
            event.get("payload", {}),
        )
    log(f"posted {len(events)} blue events for {episode_id}")
    return True


def main():
    log(f"blue agent up — backend={BACKEND}  poll={POLL_INTERVAL}s")
    while True:
        try:
            did_work = step()
            if AGENT_RUN_ONCE:
                return
            if not did_work:
                time.sleep(POLL_INTERVAL)
        except Exception as e:
            log(f"error: {e}")
            traceback.print_exc()
            if AGENT_RUN_ONCE:
                raise
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
