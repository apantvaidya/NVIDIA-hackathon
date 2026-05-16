"""Executor Agent runner — applies Blue-approved plans.

Polls the backend every POLL_INTERVAL seconds for episodes in status
`waiting_for_executor_narrator`. For each one:
  1. Reads the latest final action from the backend.
  2. (Optionally) calls openclaw `executor-agent` for a confirmation decision.
  3. POSTs the request to the real /execute/* endpoint.
  4. POSTs EXECUTOR_ACTION and EXECUTION_RESULT events.
  5. Marks the episode complete.
"""

import os
import time
import traceback

import requests

from agent_common import (
    BACKEND, call_openclaw, episodes_with_status, get, log, post, post_event,
)

POLL_INTERVAL = int(os.environ.get("EXECUTOR_POLL_INTERVAL", "2"))

ALLOWED_ENDPOINTS = {
    "/execute/transfer-inventory",
    "/execute/update-production-schedule",
    "/execute/update-supplier-allocation",
    "/execute/update-reorder-point",
    "/execute/update-lane",
}
FORBIDDEN_TOKENS = ("/tick", "/reset", "/simulate/")


def safe_execute(endpoint, body):
    try:
        r = requests.post(BACKEND + endpoint, json=body, timeout=60)
        try:
            data = r.json()
        except Exception:
            data = {"status_code": r.status_code, "text": r.text[:500]}
        ok = (r.status_code < 400) and (data.get("success") is not False)
        return ok, data
    except Exception as e:
        return False, {"error": str(e)}


def mock_executor(plan_payload):
    return {
        "execution_status": "ready",
        "tool_called": plan_payload.get("action_type"),
        "endpoint": plan_payload.get("execute_endpoint"),
        "payload_sent": plan_payload.get("request"),
        "summary": "Mock executor decision (no openclaw on PATH).",
    }


def step():
    pending = episodes_with_status("waiting_for_executor_narrator")
    if not pending:
        return False
    episode = pending[-1]
    episode_id = episode["id"]

    plan = get(f"/api/agent/episodes/{episode_id}/latest-final-action")
    payload = plan.get("payload", {})
    endpoint = payload.get("execute_endpoint", "")
    request_body = payload.get("request", {})

    if any(tok in endpoint for tok in FORBIDDEN_TOKENS) or endpoint not in ALLOWED_ENDPOINTS:
        post_event(episode_id, "EXECUTION_RESULT", "Refused",
                   "Endpoint not in allowed list.",
                   {"status": "refused", "endpoint": endpoint})
        post(f"/api/agent/episodes/{episode_id}/complete", {})
        log(f"refused {episode_id} endpoint={endpoint}")
        return True

    try:
        decision = call_openclaw("executor-agent", {"plan": payload, "sim_base_url": BACKEND})
    except FileNotFoundError:
        decision = mock_executor(payload)

    ok, response = safe_execute(endpoint, request_body)
    status = "success" if ok else "failed"

    post_event(episode_id, "EXECUTOR_ACTION", f"Called {endpoint}",
               "Submitted approved action to real /execute endpoint.",
               {"endpoint": endpoint, "request": request_body, "agent_decision": decision})
    post_event(episode_id, "EXECUTION_RESULT", f"Execution {status}",
               "Backend confirmation captured.",
               {"status": status, "response": response})
    post(f"/api/agent/episodes/{episode_id}/complete", {})
    log(f"executed {episode_id} status={status}")
    return True


def main():
    log(f"executor agent up — backend={BACKEND}  poll={POLL_INTERVAL}s")
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
