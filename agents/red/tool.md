# Red Agent Tools

## Backend Base URL
Use:

```text
BACKEND_URL
```

Default for local development:

```text
http://localhost:8000
```

## Required Tools

### Get Episodes
```http
GET /api/agent/episodes
```

Use this only if you need to find active episodes. Red usually creates a new episode or receives an episode ID from an external orchestrator.

### Create Episode
```http
POST /api/agent/episodes
```

Use when Red is responsible for starting the decision cycle.

Request:

```json
{
  "simulation_id": "default",
  "trigger": {
    "type": "manual",
    "summary": "Red scan requested."
  },
  "user_preferences": {
    "profile": "balanced",
    "weights": {
      "profit": 0.25,
      "service": 0.35,
      "cost": 0.25,
      "emissions": 0.15
    }
  }
}
```

### Get Episode Context
```http
GET /api/agent/episodes/{episode_id}/context
```

This is Red's main read tool.

Use it to inspect:

- `current_state`
- `current_kpis`
- `recent_alerts`
- `recent_event_history`
- `action_history`
- `available_action_endpoints`
- `user_preferences`
- `output_contract`

### Submit Red Plan
```http
POST /api/agent/events
```

Request:

```json
{
  "episode_id": "ep_xxx",
  "agent_id": "red_agent",
  "event_type": "RED_PLAN",
  "title": "Short proposal title",
  "summary": "One-paragraph explanation of the proposed action.",
  "payload": {
    "observed_problem": {},
    "candidate_actions_considered": [],
    "initial_recommended_action": {
      "action_type": "transfer_inventory",
      "execute_endpoint": "/execute/transfer-inventory",
      "request": {}
    },
    "reasoning": [],
    "expected_tradeoffs": {
      "improves": [],
      "worsens": [],
      "neutral": []
    },
    "confidence": 0.0
  }
}
```

## Optional Read Tools

### Current State
```http
GET /state
```

### Current KPIs
```http
GET /kpis
```

### Supply Chain Graph
```http
GET /graph
```

### Alerts History
```http
GET /alerts/history
```

### Event History
```http
GET /events/history
```

### Action History
```http
GET /actions/history
```

## Forbidden Tools
Red must not call:

```text
POST /execute/*
POST /tick
POST /reset
POST /simulation/start
POST /simulation/stop
```

Red may call `/simulate/*` only if the external agent implementation explicitly supports it, but the normal architecture leaves simulation validation to Blue.

