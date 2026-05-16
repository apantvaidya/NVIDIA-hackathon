# Blue Agent Tools

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

### List Episodes
```http
GET /api/agent/episodes
```

Find episodes with:

```text
status = waiting_for_blue_revised_plan
```

### Get Episode Context
```http
GET /api/agent/episodes/{episode_id}/context
```

This is Blue's main read tool.

Use `prior_agent_events` to find the most recent `RED_PLAN`.

### Submit Agent Event
```http
POST /api/agent/events
```

Blue submits:

- `BLUE_ASSESSMENT`
- `BLUE_REVISED_PLAN` if approved or revised

## Simulation Tools
Simulation tools are read-only. They deep-copy backend state and do not mutate the live world.

### Simulate Inventory Transfer
```http
POST /simulate/transfer-inventory
```

Request:

```json
{
  "product_id": "sku_standard",
  "from_node": "chicago_hub",
  "to_node": "west_coast_dc",
  "units": 500,
  "lane_id": "chicago_to_west_rail",
  "mode": null,
  "weeks_to_simulate": 1
}
```

Use this to compare rail, truck, air, and local transfer consequences.

### Simulate Production Schedule
```http
POST /simulate/update-production-schedule
```

Request:

```json
{
  "production_node_id": "central_factory",
  "new_product_id": "sku_bulk_pack",
  "weeks_to_simulate": 2
}
```

Use this to test changeover cost, output disruption, and downstream service impact.

### Simulate Supplier Allocation
```http
POST /simulate/update-supplier-allocation
```

Request:

```json
{
  "allocations": {
    "supplier_a": 0.55,
    "supplier_b": 0.45
  }
}
```

Use this to validate sourcing cost versus supplier risk.

### Simulate Reorder Point
```http
POST /simulate/update-reorder-point
```

Request:

```json
{
  "warehouse_id": "west_coast_dc",
  "product_id": "sku_standard",
  "new_reorder_point": 1800
}
```

Use this to validate inventory buffer versus holding cost and expiry risk.

## Optional Read Tools

### Current State
```http
GET /state
```

### Current KPIs
```http
GET /kpis
```

### Graph
```http
GET /graph
```

### Alerts
```http
GET /alerts/history
```

## Forbidden Tools
Blue must not call:

```text
POST /execute/*
POST /tick
POST /reset
POST /simulation/start
POST /simulation/stop
```

## Output Tool Use Pattern

1. `GET /api/agent/episodes`
2. Pick one `waiting_for_blue_revised_plan` episode.
3. `GET /api/agent/episodes/{episode_id}/context`
4. Read latest `RED_PLAN`.
5. Call the appropriate `/simulate/*` endpoint if available.
6. Submit `BLUE_ASSESSMENT`.
7. If approved or revised, submit `BLUE_REVISED_PLAN`.

