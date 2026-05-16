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
    BACKEND, call_openclaw, episodes_with_status, get, log, post_event,
)

POLL_INTERVAL = int(os.environ.get("BLUE_POLL_INTERVAL", "2"))


def mock_blue(ctx):
    red_plan_event = next(
        (e for e in reversed(ctx.get("prior_agent_events", [])) if e.get("event_type") == "RED_PLAN"),
        None,
    )
    plan_payload = red_plan_event["payload"] if red_plan_event else {}
    return [
        {
            "event_type": "BLUE_ASSESSMENT",
            "title": "Mock approval",
            "summary": "OpenClaw not invoked. Replace with real reasoning by installing openclaw.",
            "payload": {
                "approved": True, "decision": "approved", "risk_level": "low",
                "optimization_score": 0.7, "human_approval_required": False,
                "simulation_evidence": {"_mock": True},
            },
        },
        {
            "event_type": "BLUE_REVISED_PLAN",
            "title": "Mock revision (pass-through)",
            "summary": "Same plan Red proposed; no real validation performed.",
            "payload": plan_payload,
        },
    ]


def step():
    pending = episodes_with_status("waiting_for_blue_revised_plan")
    if not pending:
        return False
    episode = pending[-1]
    episode_id = episode["id"]
    ctx = get(f"/api/agent/episodes/{episode_id}/context")
    red_plan = next(
        (e for e in reversed(ctx.get("prior_agent_events", [])) if e.get("event_type") == "RED_PLAN"),
        None,
    )
    message = {
        "red_plan": red_plan["payload"] if red_plan else None,
        "prior_agent_events": ctx.get("prior_agent_events"),
        "current_state": ctx.get("current_state"),
        "current_kpis": ctx.get("current_kpis"),
        "recent_alerts": ctx.get("recent_alerts"),
        "user_preferences": ctx.get("user_preferences"),
        "available_action_endpoints": ctx.get("available_action_endpoints"),
        "sim_base_url": BACKEND,
    }
    try:
        events = call_openclaw("blue-agent", message)
    except FileNotFoundError:
        log("openclaw not found — using mock_blue.")
        events = mock_blue(ctx)
    if isinstance(events, dict):
        events = [events]
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
            if not step():
                time.sleep(POLL_INTERVAL)
        except Exception as e:
            log(f"error: {e}")
            traceback.print_exc()
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
