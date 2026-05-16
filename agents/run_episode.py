"""Run one ChainPilot agent episode from start to finish.

This is the MVP coordinator: no polling loops, no random episode pickup.
It drives exactly one episode through:
RED_PLAN -> BLUE_ASSESSMENT -> BLUE_REVISED_PLAN -> EXECUTOR_ACTION ->
EXECUTION_RESULT -> KPI_EVALUATION -> NARRATION.
"""

import argparse
import os
from typing import Any, Dict

import requests

import agent_common
from agent_common import call_openclaw, log, normalize_transfer_request
from blue_agent import compact_kpis as compact_blue_kpis
from blue_agent import compact_state as compact_blue_state
from blue_agent import normalize_blue_events
from red_agent import compact_kpis as compact_red_kpis
from red_agent import compact_state as compact_red_state
from red_agent import normalize_red_plan


ALLOWED_EXECUTE_ENDPOINTS = {
    "/execute/transfer-inventory",
    "/execute/update-production-schedule",
    "/execute/update-supplier-allocation",
    "/execute/update-reorder-point",
    "/execute/update-lane",
}


def configure_backend(url: str) -> None:
    agent_common.BACKEND = url.rstrip("/")


def api_get(path: str) -> Any:
    response = requests.get(agent_common.BACKEND + path, timeout=30)
    response.raise_for_status()
    return response.json()


def api_post(path: str, body: Dict[str, Any] | None = None) -> Any:
    response = requests.post(agent_common.BACKEND + path, json=body or {}, timeout=60)
    response.raise_for_status()
    return response.json()


def post_event(episode_id: str, agent_id: str, event_type: str, title: str, summary: str, payload: Dict[str, Any]) -> Any:
    return api_post("/api/agent/events", {
        "episode_id": episode_id,
        "agent_id": agent_id,
        "event_type": event_type,
        "title": title,
        "summary": summary,
        "payload": payload,
    })


def create_or_get_episode(episode_id: str | None) -> Dict[str, Any]:
    if episode_id:
        return api_get(f"/api/agent/episodes/{episode_id}")
    return api_post("/api/agent/episodes", {
        "simulation_id": "default",
        "trigger": {
            "type": "manual",
            "summary": "One-shot OpenClaw agent episode run.",
        },
        "user_preferences": {
            "profile": "balanced",
            "weights": {
                "profit": 0.25,
                "service": 0.35,
                "cost": 0.25,
                "emissions": 0.15,
            },
        },
    })


def timeline_events(episode_id: str) -> list[Dict[str, Any]]:
    return api_get(f"/api/agent/episodes/{episode_id}/timeline").get("events", [])


def latest_event(episode_id: str, event_type: str) -> Dict[str, Any] | None:
    for event in reversed(timeline_events(episode_id)):
        if event.get("event_type") == event_type:
            return event
    return None


def set_openclaw_session(session_id: str) -> None:
    agent_common.OPENCLAW_SESSION_ID = session_id


def run_red(episode_id: str, openclaw_agent: str) -> Dict[str, Any]:
    existing = latest_event(episode_id, "RED_PLAN")
    if existing:
        log(f"red skip: episode already has RED_PLAN {existing['id']}")
        return existing

    context = api_get(f"/api/agent/episodes/{episode_id}/context")
    message = {
        "current_state": compact_red_state(context.get("current_state")),
        "current_kpis": compact_red_kpis(context.get("current_kpis")),
        "recent_alerts": (context.get("recent_alerts") or [])[-5:],
        "available_action_endpoints": context.get("available_action_endpoints"),
        "user_preferences": context.get("user_preferences"),
    }
    set_openclaw_session(f"chainpilot-red-{episode_id}")
    plan = normalize_red_plan(call_openclaw(openclaw_agent, message, prompt_name="red_agent"))
    event = post_event(episode_id, "red_agent", "RED_PLAN", plan["title"], plan["summary"], plan["payload"])
    log(f"posted RED_PLAN {event['event']['id']}")
    return event["event"]


def run_blue(episode_id: str, openclaw_agent: str) -> list[Dict[str, Any]]:
    existing = latest_event(episode_id, "BLUE_REVISED_PLAN")
    if existing:
        log(f"blue skip: episode already has BLUE_REVISED_PLAN {existing['id']}")
        return [existing]

    context = api_get(f"/api/agent/episodes/{episode_id}/context")
    red_event = latest_event(episode_id, "RED_PLAN")
    if not red_event:
        raise RuntimeError(f"Episode {episode_id} has no RED_PLAN.")

    message = {
        "red_plan": red_event.get("payload"),
        "current_state": compact_blue_state(context.get("current_state")),
        "current_kpis": compact_blue_kpis(context.get("current_kpis")),
        "recent_alerts": (context.get("recent_alerts") or [])[-5:],
        "user_preferences": context.get("user_preferences"),
        "available_action_endpoints": context.get("available_action_endpoints"),
    }
    set_openclaw_session(f"chainpilot-blue-{episode_id}")
    blue_events = normalize_blue_events(
        call_openclaw(openclaw_agent, message, prompt_name="blue_agent"),
        red_event.get("payload", {}),
    )

    posted = []
    for event in blue_events:
        accepted = post_event(
            episode_id,
            "blue_agent",
            event["event_type"],
            event.get("title", event["event_type"]),
            event.get("summary", ""),
            event.get("payload", {}),
        )
        posted.append(accepted["event"])
        log(f"posted {event['event_type']} {accepted['event']['id']}")
    return posted


def metric_delta(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    def pick(kpis: Dict[str, Any], path: tuple[str, ...]) -> Any:
        value: Any = kpis
        for key in path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

    metrics = {
        "estimated_profit": (("financial", "estimated_profit")),
        "transport_cost": (("financial", "transport_cost")),
        "stockout_penalty": (("financial", "stockout_penalty")),
        "vendor_compliance_fines": (("financial", "vendor_compliance_fines")),
        "air_freight_share": (("logistics", "air_freight_share")),
        "supplier_risk_index": (("sourcing", "supplier_risk_index")),
    }
    delta = {}
    for name, path in metrics.items():
        before_value = pick(before, path)
        after_value = pick(after, path)
        if isinstance(before_value, (int, float)) and isinstance(after_value, (int, float)):
            delta[name] = round(after_value - before_value, 4)
    return delta


def summarize_tradeoffs(delta: Dict[str, Any]) -> Dict[str, list[str]]:
    improves: list[str] = []
    worsens: list[str] = []
    neutral: list[str] = []
    higher_is_better = {"estimated_profit"}
    for key, value in delta.items():
        if not isinstance(value, (int, float)) or value == 0:
            neutral.append(key)
        elif key in higher_is_better:
            (improves if value > 0 else worsens).append(key)
        else:
            (improves if value < 0 else worsens).append(key)
    return {"improves": improves, "worsens": worsens, "neutral": neutral}


def run_executor(episode_id: str, openclaw_agent: str, skip_openclaw_executor: bool = False) -> Dict[str, Any]:
    existing = latest_event(episode_id, "EXECUTION_RESULT")
    if existing:
        log(f"executor skip: episode already has EXECUTION_RESULT {existing['id']}")
        return existing

    latest_action = api_get(f"/api/agent/episodes/{episode_id}/latest-final-action")
    payload = normalize_transfer_request(latest_action.get("payload", {}))
    endpoint = payload.get("execute_endpoint")
    request_body = payload.get("request", {})
    if endpoint not in ALLOWED_EXECUTE_ENDPOINTS:
        raise RuntimeError(f"Refusing endpoint {endpoint!r}; not in allowed execute endpoints.")

    before_kpis = api_get("/kpis")
    decision: Dict[str, Any] = {
        "execution_status": "ready",
        "endpoint": endpoint,
        "summary": "Executor applying Blue-approved action.",
    }
    if not skip_openclaw_executor:
        set_openclaw_session(f"chainpilot-executor-{episode_id}")
        decision = call_openclaw(openclaw_agent, {"plan": payload}, prompt_name="executor_agent")

    action_event = post_event(
        episode_id,
        "executor_narrator_agent",
        "EXECUTOR_ACTION",
        f"Called {endpoint}",
        "Submitted approved action to real /execute endpoint.",
        {"endpoint": endpoint, "request": request_body, "agent_decision": decision},
    )
    log(f"posted EXECUTOR_ACTION {action_event['event']['id']}")

    response = api_post(endpoint, request_body)
    status = "success" if response.get("success") is not False else "failed"
    result_event = post_event(
        episode_id,
        "executor_narrator_agent",
        "EXECUTION_RESULT",
        f"Execution {status}",
        "Backend confirmation captured.",
        {"status": status, "response": response},
    )
    log(f"posted EXECUTION_RESULT {result_event['event']['id']}")

    after_kpis = api_get("/kpis")
    delta = metric_delta(before_kpis, after_kpis)
    tradeoffs = summarize_tradeoffs(delta)
    kpi_event = post_event(
        episode_id,
        "executor_narrator_agent",
        "KPI_EVALUATION",
        "KPI impact captured",
        "Compared KPI snapshot before and after execution.",
        {
            "before_kpis": before_kpis,
            "after_kpis": after_kpis,
            "kpi_delta": delta,
            "tradeoff_summary": tradeoffs,
        },
    )
    log(f"posted KPI_EVALUATION {kpi_event['event']['id']}")

    narration = {
        "headline": "Approved action executed",
        "plain_english_summary": (
            f"Executor called {endpoint}. Improvements: {', '.join(tradeoffs['improves']) or 'none obvious'}. "
            f"Tradeoffs worsened: {', '.join(tradeoffs['worsens']) or 'none obvious'}."
        ),
        "what_improved": tradeoffs["improves"],
        "what_worsened": tradeoffs["worsens"],
        "operator_takeaway": "This action reflects the Blue-approved tradeoff, not a universal optimum.",
    }
    narration_event = post_event(
        episode_id,
        "executor_narrator_agent",
        "NARRATION",
        narration["headline"],
        narration["plain_english_summary"],
        narration,
    )
    log(f"posted NARRATION {narration_event['event']['id']}")
    api_post(f"/api/agent/episodes/{episode_id}/complete", {})
    return result_event["event"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one ChainPilot agent episode.")
    parser.add_argument("--backend", default=os.environ.get("BACKEND_URL", "http://localhost:8000"))
    parser.add_argument("--episode", default=os.environ.get("TARGET_EPISODE_ID"))
    parser.add_argument("--openclaw-agent", default=os.environ.get("OPENCLAW_AGENT", "main"))
    parser.add_argument("--skip-openclaw-executor", action="store_true")
    args = parser.parse_args()

    configure_backend(args.backend)
    episode = create_or_get_episode(args.episode)
    episode_id = episode["id"]
    log(f"running one-shot episode {episode_id} against {agent_common.BACKEND}")
    run_red(episode_id, args.openclaw_agent)
    run_blue(episode_id, args.openclaw_agent)
    run_executor(episode_id, args.openclaw_agent, skip_openclaw_executor=args.skip_openclaw_executor)
    log(f"completed episode {episode_id}")


if __name__ == "__main__":
    main()
