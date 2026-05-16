# Executor-Narrator Agent Tools

## Backend Base URL
Use:

```text
BACKEND_URL
```

Default for local development:

```text
http://localhost:8000
```

## Required Read Tools

### List Episodes
```http
GET /api/agent/episodes
```

Find episodes with:

```text
status = waiting_for_executor_narrator
```

### Get Latest Final Action
```http
GET /api/agent/episodes/{episode_id}/latest-final-action
```

Returns:

```json
{
  "episode_id": "ep_xxx",
  "event_id": "evt_xxx",
  "event_type": "BLUE_REVISED_PLAN",
  "payload": {
    "action_type": "transfer_inventory",
    "execute_endpoint": "/execute/transfer-inventory",
    "request": {}
  }
}
```

### Get KPIs
```http
GET /kpis
```

Use before and after execution.

### Get State
```http
GET /state
```

Use after execution to capture updated world state.

### Get Timeline
```http
GET /api/agent/episodes/{episode_id}/timeline
```

Use if you need Red and Blue context for narration.

## Allowed Execute Tools
Executor-Narrator may call exactly one of these per episode.

### Execute Inventory Transfer
```http
POST /execute/transfer-inventory
```

Request:

```json
{
  "product_id": "sku_standard",
  "from_node": "chicago_hub",
  "to_node": "west_coast_dc",
  "units": 500,
  "lane_id": "chicago_to_west_rail",
  "mode": null
}
```

### Execute Production Schedule Update
```http
POST /execute/update-production-schedule
```

Request:

```json
{
  "production_node_id": "central_factory",
  "new_product_id": "sku_bulk_pack"
}
```

### Execute Supplier Allocation Update
```http
POST /execute/update-supplier-allocation
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

### Execute Reorder Point Update
```http
POST /execute/update-reorder-point
```

Request:

```json
{
  "warehouse_id": "west_coast_dc",
  "product_id": "sku_standard",
  "new_reorder_point": 1800
}
```

### Execute Lane Update
```http
POST /execute/update-lane
```

Request:

```json
{
  "lane_id": "factory_to_chicago_rail",
  "status": "active",
  "transit_weeks": 1,
  "capacity": 3000
}
```

## Event Submission Tool

### Submit Agent Event
```http
POST /api/agent/events
```

Submit:

- `EXECUTOR_ACTION`
- `EXECUTION_RESULT`
- `KPI_EVALUATION`
- `NARRATION`

### Complete Episode
```http
POST /api/agent/episodes/{episode_id}/complete
```

Optional. `NARRATION` already transitions the episode to completed.

## Optional Tick Tool
Only use if explicitly requested by the episode trigger or external orchestrator.

```http
POST /tick
```

If used, include the tick response in `EXECUTION_RESULT` and mention it in `NARRATION`.

## Forbidden Tools
Executor-Narrator must not call:

```text
POST /simulate/*
POST /reset
POST /simulation/start
POST /simulation/stop
```

Executor-Narrator must not execute an endpoint that is not listed in this file.

## Tool Use Pattern

1. `GET /api/agent/episodes`
2. Pick one `waiting_for_executor_narrator` episode.
3. `GET /api/agent/episodes/{episode_id}/latest-final-action`
4. Validate that `payload.execute_endpoint` is allowed.
5. `GET /kpis` for before snapshot.
6. Call the exact allowed `/execute/*` endpoint with `payload.request`.
7. `GET /kpis` and `GET /state` for after snapshot.
8. Submit `EXECUTOR_ACTION`.
9. Submit `EXECUTION_RESULT`.
10. Submit `KPI_EVALUATION`.
11. Submit `NARRATION`.

