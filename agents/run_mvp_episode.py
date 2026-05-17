"""Run the lightweight ChainPilot MVP episode.

This runner makes exactly one OpenClaw call. OpenClaw returns a decision
package containing Red's proposal, Blue's critique, and Blue's final plan.
Python then posts the episode events, executes the final action, and records
the KPI/narration events.
"""

import argparse
import os
from typing import Any, Dict

import requests

import agent_common
from agent_common import call_openclaw, log, normalize_transfer_request
from red_agent import compact_kpis, compact_state, normalize_red_plan
from run_episode import (
    ALLOWED_EXECUTE_ENDPOINTS,
    api_get,
    api_post,
    configure_backend,
    create_or_get_episode,
    metric_delta,
    post_event,
    summarize_tradeoffs,
)


def set_openclaw_session(session_id: str) -> None:
    agent_common.OPENCLAW_SESSION_ID = session_id


def safe_reset_backend() -> None:
    response = requests.post(agent_common.BACKEND + "/reset", json={}, timeout=60)
    response.raise_for_status()


def normalize_event_object(value: Any, default_title: str, default_summary: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Decision package section must be an object, got {type(value).__name__}.")
    if "payload" not in value and "action_type" in value:
        value = {
            "title": default_title,
            "summary": default_summary,
            "payload": value,
        }
    if "payload" not in value:
        raise ValueError(f"Decision package section missing payload: {repr(value)[:500]}")
    return {
        "title": value.get("title", default_title),
        "summary": value.get("summary", default_summary),
        "payload": value["payload"],
    }


def normalize_decision_package(raw: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(raw, dict) and raw.get("_raw_openclaw_text"):
        raise ValueError(
            "OpenClaw returned prose instead of the MVP decision JSON. "
            f"First 800 chars: {raw['_raw_openclaw_text'][:800]}"
        )
    if not isinstance(raw, dict):
        raise ValueError(f"Decision package must be a JSON object, got {type(raw).__name__}.")

    red = raw.get("red_plan") or raw.get("red") or raw.get("RED_PLAN")
    blue_assessment = (
        raw.get("blue_assessment")
        or raw.get("blue")
        or raw.get("BLUE_ASSESSMENT")
    )
    blue_final = (
        raw.get("blue_revised_plan")
        or raw.get("final_action")
        or raw.get("BLUE_REVISED_PLAN")
        or raw.get("FINAL_ACTION")
    )

    if not red or not blue_assessment or not blue_final:
        raise ValueError(
            "Decision package must include red_plan, blue_assessment, and blue_revised_plan. "
            f"Keys={list(raw.keys())}"
        )

    red_event = normalize_red_plan(normalize_event_object(
        red,
        "Red Agent Plan",
        "Red proposed one initial supply-chain action.",
    ))
    assessment_event = normalize_event_object(
        blue_assessment,
        "Blue Agent Assessment",
        "Blue assessed Red's proposed action.",
    )
    final_event = normalize_event_object(
        blue_final,
        "Blue Agent Revised Final Plan",
        "Blue selected the final action for execution.",
    )
    final_event["payload"] = normalize_transfer_request(final_event["payload"])
    return {
        "red_plan": red_event,
        "blue_assessment": assessment_event,
        "blue_revised_plan": final_event,
    }


def build_decision_message(episode_id: str) -> Dict[str, Any]:
    context = api_get(f"/api/agent/episodes/{episode_id}/context")
    return {
        "task": (
            "Return one decision package. Red proposes one feasible action. "
            "Blue critiques it and returns the final executable plan. "
            "Python will post events and execute the final action."
        ),
        "required_shape": {
            "red_plan": {
                "title": "string",
                "summary": "string",
                "payload": {
                    "action_type": "transfer_inventory",
                    "execute_endpoint": "/execute/transfer-inventory",
                    "request": {
                        "product_id": "sku_standard",
                        "from_node": "chicago_hub",
                        "to_node": "west_coast_dc",
                        "units": 900,
                        "lane_id": "chicago_to_west_rail",
                    },
                    "reasoning": ["short reason"],
                    "expected_tradeoffs": {"improves": [], "worsens": [], "neutral": []},
                    "confidence": 0.7,
                },
            },
            "blue_assessment": {
                "title": "string",
                "summary": "string",
                "payload": {
                    "decision": "approved | revised | rejected | human_approval_required",
                    "approved": True,
                    "risk_level": "low | medium | high",
                    "risks_identified": [],
                    "constraint_violations": [],
                    "what_blue_changed": [],
                    "confidence": 0.7,
                },
            },
            "blue_revised_plan": {
                "title": "string",
                "summary": "string",
                "payload": "same executable action shape as red_plan.payload",
            },
        },
        "current_state": compact_state(context.get("current_state")),
        "current_kpis": compact_kpis(context.get("current_kpis")),
        "recent_alerts": (context.get("recent_alerts") or [])[-5:],
        "available_action_endpoints": context.get("available_action_endpoints"),
        "user_preferences": context.get("user_preferences"),
    }


def get_decision_package(episode_id: str, openclaw_agent: str) -> Dict[str, Dict[str, Any]]:
    set_openclaw_session(f"chainpilot-mvp-{episode_id}")
    raw = call_openclaw(openclaw_agent, build_decision_message(episode_id), prompt_name="decision_agent")
    return normalize_decision_package(raw)


def post_decision_events(episode_id: str, package: Dict[str, Dict[str, Any]]) -> None:
    red = package["red_plan"]
    post_event(episode_id, "red_agent", "RED_PLAN", red["title"], red["summary"], red["payload"])
    log("posted RED_PLAN")

    assessment = package["blue_assessment"]
    post_event(
        episode_id,
        "blue_agent",
        "BLUE_ASSESSMENT",
        assessment["title"],
        assessment["summary"],
        assessment["payload"],
    )
    log("posted BLUE_ASSESSMENT")

    final = package["blue_revised_plan"]
    post_event(
        episode_id,
        "blue_agent",
        "BLUE_REVISED_PLAN",
        final["title"],
        final["summary"],
        final["payload"],
    )
    log("posted BLUE_REVISED_PLAN")


def execute_final_plan(episode_id: str, final_payload: Dict[str, Any]) -> None:
    payload = normalize_transfer_request(final_payload)
    endpoint = payload.get("execute_endpoint")
    request_body = payload.get("request", {})
    if endpoint not in ALLOWED_EXECUTE_ENDPOINTS:
        raise RuntimeError(f"Refusing endpoint {endpoint!r}; not in allowed execute endpoints.")

    before_kpis = api_get("/kpis")
    post_event(
        episode_id,
        "executor_narrator_agent",
        "EXECUTOR_ACTION",
        f"Called {endpoint}",
        "Submitted Blue-approved action to the real backend execute endpoint.",
        {"endpoint": endpoint, "request": request_body, "approved_plan": payload},
    )
    log("posted EXECUTOR_ACTION")

    response = api_post(endpoint, request_body)
    status = "success" if response.get("success") is not False else "failed"
    post_event(
        episode_id,
        "executor_narrator_agent",
        "EXECUTION_RESULT",
        f"Execution {status}",
        "Backend confirmation captured.",
        {"status": status, "response": response},
    )
    log("posted EXECUTION_RESULT")

    after_kpis = api_get("/kpis")
    delta = metric_delta(before_kpis, after_kpis)
    tradeoffs = summarize_tradeoffs(delta)
    post_event(
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
    log("posted KPI_EVALUATION")

    narration = {
        "headline": "MVP decision package executed",
        "plain_english_summary": (
            f"OpenClaw produced one Red/Blue decision package. ChainPilot executed {endpoint}. "
            f"Improvements: {', '.join(tradeoffs['improves']) or 'none obvious'}. "
            f"Tradeoffs worsened: {', '.join(tradeoffs['worsens']) or 'none obvious'}."
        ),
        "what_improved": tradeoffs["improves"],
        "what_worsened": tradeoffs["worsens"],
        "operator_takeaway": "This is an agent-selected test action, not a backend optimizer result.",
    }
    post_event(
        episode_id,
        "executor_narrator_agent",
        "NARRATION",
        narration["headline"],
        narration["plain_english_summary"],
        narration,
    )
    log("posted NARRATION")
    api_post(f"/api/agent/episodes/{episode_id}/complete", {})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one lightweight ChainPilot MVP episode.")
    parser.add_argument("--backend", default=os.environ.get("BACKEND_URL", "http://localhost:8000"))
    parser.add_argument("--episode", default=os.environ.get("TARGET_EPISODE_ID"))
    parser.add_argument("--openclaw-agent", default=os.environ.get("OPENCLAW_AGENT", "main"))
    parser.add_argument("--openclaw-timeout", type=int, default=int(os.environ.get("AGENT_TIMEOUT", "600")))
    parser.add_argument("--reset-first", action="store_true", help="Reset simulation and clear episodes before running.")
    args = parser.parse_args()

    configure_backend(args.backend)
    agent_common.AGENT_TIMEOUT = args.openclaw_timeout
    if args.reset_first:
        safe_reset_backend()
        log("backend reset complete")

    episode = create_or_get_episode(args.episode)
    episode_id = episode["id"]
    log(f"running MVP episode {episode_id} against {agent_common.BACKEND}")
    package = get_decision_package(episode_id, args.openclaw_agent)
    post_decision_events(episode_id, package)
    execute_final_plan(episode_id, package["blue_revised_plan"]["payload"])
    log(f"completed MVP episode {episode_id}")


if __name__ == "__main__":
    main()
