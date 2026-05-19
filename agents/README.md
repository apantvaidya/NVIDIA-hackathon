# ChainPilot Agent Runners

Python runners that connect ChainPilot episodes to OpenClaw/NVIDIA Nemotron.

For the hackathon MVP, use `run_mvp_episode.py`. It makes one OpenClaw call, receives a compact Red/Blue decision package, posts the episode events, executes Blue's final action, records KPI impact, and completes the episode.

## Recommended MVP Command

```bash
cd agents
export BACKEND_URL=https://backend-supply-utfs.onrender.com

python3 run_mvp_episode.py \
  --backend https://backend-supply-utfs.onrender.com \
  --openclaw-agent main \
  --openclaw-timeout 900 \
  --reset-first
```

## Files

```text
agents/
  agent_common.py        shared HTTP + OpenClaw helpers
  run_mvp_episode.py     recommended one-shot MVP runner
  run_episode.py         older multi-turn one-shot coordinator
  red_agent.py           legacy long-running Red runner
  blue_agent.py          legacy long-running Blue runner
  executor_agent.py      legacy long-running Executor runner
  red/agent.md           Red prompt
  blue/agent.md          Blue prompt
  executor/agent.md      Executor prompt
```

## Environment Variables

| variable | default | purpose |
|---|---:|---|
| `BACKEND_URL` | `http://localhost:8000` | ChainPilot backend URL |
| `OPENCLAW_BIN` | `openclaw` | OpenClaw CLI path |
| `OPENCLAW_AGENT` | `main` | OpenClaw agent id for `run_mvp_episode.py` |
| `AGENT_TIMEOUT` | `600` | OpenClaw timeout in seconds |
| `RED_AUTO_CREATE_EPISODES` | `0` | opt-in only for legacy Red auto episode creation |

## No Mock Fallbacks

The MVP runners are designed to use OpenClaw. Mock/fallback agent events are rejected by the backend so the demo does not accidentally show placeholder decisions.

If OpenClaw is slow, prefer shrinking the decision brief rather than sending the full simulation state.

## Event Flow

```text
RED_PLAN
-> BLUE_ASSESSMENT
-> BLUE_REVISED_PLAN
-> EXECUTOR_ACTION
-> EXECUTION_RESULT
-> KPI_EVALUATION
-> NARRATION
```

The simulator remains the world model and consequence engine. Agents choose actions and explain tradeoffs; the backend validates and executes only supported action endpoints.
