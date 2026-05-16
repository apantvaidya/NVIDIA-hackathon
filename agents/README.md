# ChainPilot Agent Runners

Three Python runners that talk to the ChainPilot backend on behalf of the
Red, Blue, and Executor OpenClaw agents.

```
agents/
  agent_common.py        shared HTTP + OpenClaw helpers
  red_agent.py           proposes one inefficiency fix per cycle
  blue_agent.py          validates and revises Red's plans
  executor_agent.py      applies Blue-approved plans
  prompts/
    red-agent.md         system prompt for OpenClaw red-agent
    blue-agent.md        system prompt for OpenClaw blue-agent
    executor-agent.md    system prompt for OpenClaw executor-agent
  requirements.txt       just `requests`
```

## Setup (per machine)

```bash
git clone https://github.com/SanjivSimha/NVIDIA-hackathon.git
cd NVIDIA-hackathon/agents
pip install -r requirements.txt
export BACKEND_URL=https://backend-supply-utfs.onrender.com
```

Then start ONE of these per box (each blocks; run in tmux/nohup/screen):

```bash
# teammate's Brev box
AGENT_ID=red_agent  python3 red_agent.py

# your Brev box (two terminals)
AGENT_ID=blue_agent              python3 blue_agent.py
AGENT_ID=executor_narrator_agent python3 executor_agent.py
```

## Environment variables

| var | default | purpose |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | base URL of the backend |
| `AGENT_ID` | `anon-agent` | string written into every event |
| `OPENCLAW_BIN` | `openclaw` | path to the openclaw binary |
| `AGENT_TIMEOUT` | `180` | seconds to wait for openclaw |
| `RED_INTERVAL_SECONDS` | `60` | how often Red scans |
| `BLUE_POLL_INTERVAL` | `2` | how often Blue polls |
| `EXECUTOR_POLL_INTERVAL` | `2` | how often Executor polls |

## Without OpenClaw

If the `openclaw` binary isn't on PATH, each runner falls back to a small
mock so you can still see the end-to-end flow on the dashboard. Install
OpenClaw and the `.md` agents under `prompts/` to use the real brains.

## Register the prompts with OpenClaw

The `.md` files in `prompts/` are the system prompts. Place / register
them wherever your OpenClaw installation expects agent definitions to
live (this varies by setup — check your OpenClaw config).

Once registered, the runners invoke them via:

```bash
openclaw agent --agent red-agent      --message "<json blob>"
openclaw agent --agent blue-agent     --message "<json blob>"
openclaw agent --agent executor-agent --message "<json blob>"
```

The runners parse the first JSON object/array from stdout (ignoring
banner / log noise) and submit the corresponding events to the backend.
