"""Red Agent runner — proposes one inefficiency fix per cycle.

Runs forever. Every INTERVAL_SECONDS:
  1. Creates a new episode.
  2. Fetches the world snapshot from the backend.
  3. Calls openclaw `red-agent` to produce a plan (or falls back to a mock).
  4. POSTs the plan as a RED_PLAN event.
"""

import os
import time
import traceback

from agent_common import (
    BACKEND, call_openclaw, get, log, post, post_event,
)

INTERVAL_SECONDS = int(os.environ.get("RED_INTERVAL_SECONDS", "60"))


def mock_red(_message):
    return {
        "title": "Mock plan: small balancing transfer",
        "summary": "OpenClaw not invoked. Replace with real reasoning by installing openclaw.",
        "payload": {
            "action_type": "transfer_inventory",
            "execute_endpoint": "/execute/transfer-inventory",
            "request": {
                "product_id": "sku_standard",
                "from_node": "chicago_hub",
                "to_node": "west_coast_dc",
                "units": 100,
                "lane_id": "chicago_to_west_rail",
            },
            "reasoning": ["mock fallback — no openclaw on PATH"],
            "expected_tradeoffs": {"improves": ["west_coast_service"], "worsens": ["transport_cost"], "neutral": []},
        },
    }


def run_once():
    episode = post("/api/agent/episodes", {"trigger": {"reason": "red_scan"}})
    episode_id = episode["id"]
    ctx = get(f"/api/agent/episodes/{episode_id}/context")
    message = {
        "current_state": ctx.get("current_state"),
        "current_kpis": ctx.get("current_kpis"),
        "recent_alerts": ctx.get("recent_alerts"),
        "recent_event_history": ctx.get("recent_event_history"),
        "action_history": ctx.get("action_history"),
        "available_action_endpoints": ctx.get("available_action_endpoints"),
        "user_preferences": ctx.get("user_preferences"),
        "output_contract": ctx.get("output_contract"),
    }
    try:
        plan = call_openclaw("red-agent", message)
    except FileNotFoundError:
        log("openclaw not found — using mock_red. Set OPENCLAW_BIN or install openclaw to use the real brain.")
        plan = mock_red(message)
    post_event(episode_id, "RED_PLAN", plan["title"], plan["summary"], plan["payload"])
    log(f"posted RED_PLAN for {episode_id}")


def main():
    log(f"red agent up — backend={BACKEND}  interval={INTERVAL_SECONDS}s")
    while True:
        try:
            run_once()
        except Exception as e:
            log(f"error: {e}")
            traceback.print_exc()
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
