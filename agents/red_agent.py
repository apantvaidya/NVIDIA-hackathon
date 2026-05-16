"""Red Agent runner — proposes one inefficiency fix per cycle.

Runs forever. Every INTERVAL_SECONDS:
  1. Looks for an active episode that still needs a RED_PLAN.
  2. Creates one only when no unfinished episode already exists.
  3. Fetches the world snapshot from the backend.
  4. Calls OpenClaw to produce a plan.
  5. POSTs the plan as a RED_PLAN event.
"""

import os
import time
import traceback

from agent_common import (
    AGENT_RUN_ONCE, BACKEND, TARGET_EPISODE_ID, call_openclaw, get, log,
    normalize_transfer_request, post, post_event, timeline_events,
)

INTERVAL_SECONDS = int(os.environ.get("RED_INTERVAL_SECONDS", "60"))
OPENCLAW_AGENT = os.environ.get("RED_OPENCLAW_AGENT", "red-agent")
UNFINISHED_STATUSES = {
    "active",
    "waiting_for_red_plan",
    "waiting_for_blue_revised_plan",
    "waiting_for_executor_narrator",
    "executed",
}


def compact_state(state):
    """Send a tiny planning summary instead of the full simulation object."""
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
    production = {
        node_id: {
            "active_product_id": node.get("active_product_id"),
            "weekly_capacity_units": node.get("weekly_capacity_units"),
            "changeover_remaining": node.get("current_changeover_remaining_weeks"),
        }
        for node_id, node in nodes.items()
        if node.get("node_type") == "production"
    }
    return {
        "time_step": state.get("time_step"),
        "virtual_week": state.get("virtual_week"),
        "simulation_status": state.get("simulation_status"),
        "product_ids": list((state.get("products") or {}).keys()),
        "distribution": distribution,
        "production": production,
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


def normalize_red_plan(plan):
    """Accept either the desired object or a one-item/event-wrapper list."""
    if isinstance(plan, dict) and plan.get("_raw_openclaw_text"):
        raise ValueError(
            "OpenClaw returned prose instead of JSON. First 800 chars: "
            f"{plan['_raw_openclaw_text'][:800]}"
        )
    if isinstance(plan, list):
        red_items = [
            item for item in plan
            if isinstance(item, dict) and item.get("event_type") in {None, "RED_PLAN"}
        ]
        plan = red_items[0] if red_items else plan[0]
    if not isinstance(plan, dict):
        raise ValueError(f"Red output must be a JSON object, got {type(plan).__name__}: {repr(plan)[:500]}")
    if "event_type" in plan and plan.get("payload") and plan.get("event_type") == "RED_PLAN":
        return {
            "title": plan.get("title", "Red Agent Plan"),
            "summary": plan.get("summary", "Red proposed one supply-chain action."),
            "payload": plan["payload"],
        }
    if "payload" not in plan and "action_type" in plan:
        plan = {
            "title": "Red Agent Plan",
            "summary": "Red proposed one supply-chain action.",
            "payload": plan,
        }
    if "payload" not in plan and "initial_recommended_action" in plan:
        plan = {
            "title": plan.get("title", "Red Agent Plan"),
            "summary": plan.get("summary") or plan.get("observed_problem", {}).get("summary") or "Red proposed one supply-chain action.",
            "payload": {
                **plan["initial_recommended_action"],
                "observed_problem": plan.get("observed_problem"),
                "candidate_actions_considered": plan.get("candidate_actions_considered", []),
                "reasoning": plan.get("reasoning", []),
                "expected_tradeoffs": plan.get("expected_tradeoffs", {}),
                "confidence": plan.get("confidence"),
            },
        }
    if "payload" not in plan:
        raise ValueError(f"Red output missing payload. Keys={list(plan.keys())}. Output={repr(plan)[:800]}")
    plan["payload"] = normalize_transfer_request(plan["payload"])
    return {
        "title": plan.get("title", "Red Agent Plan"),
        "summary": plan.get("summary", "Red proposed one supply-chain action."),
        "payload": plan["payload"],
    }


def _episode_has_red_plan(episode_id):
    return any(event.get("event_type") == "RED_PLAN" for event in timeline_events(episode_id))


def get_episode_for_red():
    if TARGET_EPISODE_ID:
        episode = get(f"/api/agent/episodes/{TARGET_EPISODE_ID}")
        if _episode_has_red_plan(TARGET_EPISODE_ID):
            log(f"skip: target episode {TARGET_EPISODE_ID} already has RED_PLAN")
            return None
        if episode.get("status") not in {"active", "waiting_for_red_plan"}:
            log(f"skip: target episode {TARGET_EPISODE_ID} is {episode.get('status')}")
            return None
        return episode

    episodes = get("/api/agent/episodes")

    for episode in episodes:
        if episode.get("status") in {"active", "waiting_for_red_plan"} and not _episode_has_red_plan(episode["id"]):
            return episode

    unfinished = [episode for episode in episodes if episode.get("status") in UNFINISHED_STATUSES]
    if unfinished:
        log(f"waiting: episode {unfinished[0]['id']} is still {unfinished[0].get('status')}")
        return None

    return post("/api/agent/episodes", {
        "trigger": {
            "type": "auto",
            "summary": "Red scan requested because no unfinished episode exists.",
        }
    })


def run_once():
    episode = get_episode_for_red()
    if not episode:
        return
    episode_id = episode["id"]
    ctx = get(f"/api/agent/episodes/{episode_id}/context")
    message = {
        "current_state": compact_state(ctx.get("current_state")),
        "current_kpis": compact_kpis(ctx.get("current_kpis")),
        "recent_alerts": (ctx.get("recent_alerts") or [])[-5:],
        "available_action_endpoints": ctx.get("available_action_endpoints"),
        "user_preferences": ctx.get("user_preferences"),
    }
    plan = normalize_red_plan(call_openclaw(OPENCLAW_AGENT, message, prompt_name="red_agent"))
    post_event(episode_id, "RED_PLAN", plan["title"], plan["summary"], plan["payload"])
    log(f"posted RED_PLAN for {episode_id}")
    return True


def main():
    log(f"red agent up — backend={BACKEND}  interval={INTERVAL_SECONDS}s")
    while True:
        try:
            did_work = run_once()
            if AGENT_RUN_ONCE:
                return
        except Exception as e:
            log(f"error: {e}")
            traceback.print_exc()
            if AGENT_RUN_ONCE:
                raise
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
