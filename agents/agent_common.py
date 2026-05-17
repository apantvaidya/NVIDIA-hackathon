"""Shared helpers for the Red / Blue / Executor agent runners."""

import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

import requests


BACKEND = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
AGENT_ID = os.environ.get("AGENT_ID", "anon-agent")
OPENCLAW_BIN = os.environ.get("OPENCLAW_BIN", "openclaw")
AGENT_TIMEOUT = int(os.environ.get("AGENT_TIMEOUT", "600"))
OPENCLAW_SESSION_ID = os.environ.get("OPENCLAW_SESSION_ID", f"chainpilot-{AGENT_ID}")
TARGET_EPISODE_ID = os.environ.get("TARGET_EPISODE_ID")
AGENT_RUN_ONCE = os.environ.get("AGENT_RUN_ONCE", "1" if TARGET_EPISODE_ID else "0") == "1"

SHORT_PROMPTS = {
    "red_agent": (
        "You are ChainPilot Red Agent. Your entire response must be one parseable JSON object. "
        "Start with { and end with }. No prose, no markdown, no analysis outside JSON. "
        "Required top-level keys: title, summary, payload. The payload must contain action_type, "
        "execute_endpoint, request, reasoning, expected_tradeoffs, and confidence. "
        "Use backend request fields from_node and to_node, never from_location or to_location. "
        "Propose exactly one action. Keep reasoning to 3 short strings. Do not call tools or backend APIs. "
        "Valid transfer request example for this demo: {\"product_id\":\"sku_standard\","
        "\"from_node\":\"chicago_hub\",\"to_node\":\"west_coast_dc\",\"units\":900,"
        "\"lane_id\":\"chicago_to_west_rail\"}."
    ),
    "blue_agent": (
        "You are ChainPilot Blue Agent. Your entire response must be one parseable JSON array. "
        "No prose, no markdown, no analysis outside JSON. Include BLUE_ASSESSMENT "
        "and, unless rejected, BLUE_REVISED_PLAN. Do not call tools or backend APIs. "
        "Blue critiques and revises Red's plan; Red does not revise again. Keep each summary short. "
        "Use backend request fields from_node and to_node, never from_location or to_location."
    ),
    "executor_agent": (
        "You are ChainPilot Executor-Narrator Agent. Your entire response must be one parseable "
        "JSON object. No prose, no markdown. Describe whether the provided plan is safe to execute. "
        "Do not call tools or backend APIs."
    ),
    "decision_agent": (
        "You are the ChainPilot MVP Decision Agent. Your entire response must be one parseable JSON "
        "object. Start with { and end with }. No prose, no markdown, no analysis outside JSON. "
        "Return exactly three top-level keys: red_plan, blue_assessment, blue_revised_plan. "
        "red_plan must have title, summary, payload. blue_assessment must have title, summary, payload. "
        "blue_revised_plan must have title, summary, payload. The final executable action must be in "
        "blue_revised_plan.payload. Use only provided endpoint names and IDs. Use backend request fields "
        "from_node and to_node, never from_location or to_location. Do not call tools or backend APIs. "
        "Keep all reasoning arrays short."
    ),
}


def log(msg: str) -> None:
    print(f"[{AGENT_ID}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def get(path: str) -> Any:
    r = requests.get(BACKEND + path, timeout=30)
    r.raise_for_status()
    return r.json()


def post(path: str, body: Optional[Dict[str, Any]] = None) -> Any:
    r = requests.post(BACKEND + path, json=body or {}, timeout=60)
    r.raise_for_status()
    return r.json()


def post_event(episode_id: str, event_type: str, title: str, summary: str, payload: Dict[str, Any]) -> Any:
    return post("/api/agent/events", {
        "episode_id": episode_id,
        "agent_id": AGENT_ID,
        "event_type": event_type,
        "title": title,
        "summary": summary,
        "payload": payload,
    })


def episodes_with_status(status: str) -> List[Dict[str, Any]]:
    eps = get("/api/agent/episodes")
    return [e for e in eps if e.get("status") == status]


def timeline_events(episode_id: str) -> List[Dict[str, Any]]:
    timeline = get(f"/api/agent/episodes/{episode_id}/timeline")
    return timeline.get("events", [])


def normalize_transfer_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize common LLM aliases into backend request field names."""
    request = payload.get("request")
    if not isinstance(request, dict):
        return payload
    if "from_node" not in request and "from_location" in request:
        request["from_node"] = request.pop("from_location")
    if "to_node" not in request and "to_location" in request:
        request["to_node"] = request.pop("to_location")
    if payload.get("action_type") == "transfer_inventory" and not request.get("lane_id"):
        from_node = request.get("from_node")
        to_node = request.get("to_node")
        if from_node == "chicago_hub" and to_node == "west_coast_dc":
            request["lane_id"] = "chicago_to_west_rail"
        elif from_node == "west_coast_dc" and to_node == "chicago_hub":
            request["lane_id"] = "west_to_chicago_truck"
    return payload


# ---------------------------------------------------------------------------
# OpenClaw invocation + JSON extraction
# ---------------------------------------------------------------------------

def extract_json(text: str) -> Optional[Any]:
    """Find the first valid top-level JSON object or array in noisy text."""
    if not text:
        return None
    text = text.strip()
    if text and text[0] in "{[":
        try:
            return json.loads(text)
        except Exception:
            pass
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    n = len(text)
    for start in range(n):
        if text[start] not in "{[":
            continue
        open_ch = text[start]
        close_ch = "}" if open_ch == "{" else "]"
        depth = 0
        in_str = False
        esc = False
        for i in range(start, n):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        break
    return None


def load_agent_prompt(prompt_name: str) -> str:
    """Use compact prompts; full markdown prompts are too large for CLI calls."""
    return SHORT_PROMPTS.get(prompt_name, SHORT_PROMPTS["red_agent"])


def call_openclaw(agent_name: str, message_obj: Dict[str, Any], prompt_name: Optional[str] = None) -> Any:
    """Run an OpenClaw agent and parse JSON from stdout.

    Raises immediately if OpenClaw is unavailable or returns non-JSON.
    """
    role_prompt = load_agent_prompt(prompt_name or agent_name)
    message = json.dumps({
        "chainpilot_runner_contract": {
            "important": "Return JSON only. Do not call backend APIs or tools. Python will submit events.",
        },
        "agent_instructions": role_prompt,
        "input": message_obj,
    })
    completed = subprocess.run(
        [
            OPENCLAW_BIN, "agent",
            "--agent", agent_name,
            "--session-id", OPENCLAW_SESSION_ID,
            "--json",
            "--thinking", os.environ.get("OPENCLAW_THINKING", "off"),
            "--timeout", str(AGENT_TIMEOUT),
            "--message", message,
        ],
        capture_output=True, text=True, timeout=AGENT_TIMEOUT,
    )
    parsed = extract_json(completed.stdout) or extract_json(completed.stderr)
    if isinstance(parsed, str):
        nested = extract_json(parsed)
        if nested is not None:
            parsed = nested
    if isinstance(parsed, dict):
        payloads = parsed.get("result", {}).get("payloads")
        if isinstance(payloads, list):
            for payload in payloads:
                if isinstance(payload, dict) and isinstance(payload.get("text"), str):
                    nested = extract_json(payload["text"])
                    if nested is not None:
                        return nested
            text_parts = [
                payload.get("text", "")
                for payload in payloads
                if isinstance(payload, dict) and isinstance(payload.get("text"), str)
            ]
            if text_parts:
                return {"_raw_openclaw_text": "\n".join(text_parts)}
        for key in ("reply", "response", "message", "content", "text", "output"):
            value = parsed.get(key)
            if isinstance(value, str):
                nested = extract_json(value)
                if nested is not None:
                    return nested
            elif isinstance(value, (dict, list)):
                return value
    if parsed is None:
        raise RuntimeError(
            f"no JSON in {agent_name} output (rc={completed.returncode})\n"
            f"stdout-tail: {completed.stdout[-500:]}\n"
            f"stderr-tail: {completed.stderr[-500:]}"
        )
    return parsed
