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
AGENT_TIMEOUT = int(os.environ.get("AGENT_TIMEOUT", "180"))


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


def call_openclaw(agent_name: str, message_obj: Dict[str, Any]) -> Any:
    """Run an OpenClaw agent and parse JSON from stdout.

    Raises FileNotFoundError if OpenClaw isn't installed — callers can catch
    that and use a mock fallback for local testing without OpenClaw.
    """
    message = json.dumps(message_obj)
    completed = subprocess.run(
        [OPENCLAW_BIN, "agent", "--agent", agent_name, "--message", message],
        capture_output=True, text=True, timeout=AGENT_TIMEOUT,
    )
    parsed = extract_json(completed.stdout) or extract_json(completed.stderr)
    if parsed is None:
        raise RuntimeError(
            f"no JSON in {agent_name} output (rc={completed.returncode})\n"
            f"stdout-tail: {completed.stdout[-500:]}\n"
            f"stderr-tail: {completed.stderr[-500:]}"
        )
    return parsed
