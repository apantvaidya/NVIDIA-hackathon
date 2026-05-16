# ChainPilot Simulation Backend

ChainPilot is an autonomous supply-chain simulation backend for agent experiments. It is a world model and consequence engine, not an optimizer: agents decide what to test, and the simulator returns state changes, KPI deltas, constraint failures, and tradeoffs.

## Industrial Sandbox

The current network is a multi-tier enterprise supply chain:

- Tier 0 sourcing: `domestic_oat_co_op`, `import_cocoa_port`
- Tier 1 production: `central_factory`, `co_packer_plant`
- Tier 2 distribution: `chicago_hub`, `west_coast_dc`, `overflow_3pl`
- Tier 3 demand: `big_box_retail`, `direct_to_consumer`

The portfolio includes:

- `sku_standard`: Standard Energy Bar Case
- `sku_bulk_pack`: Bulk Retail Pack

Warehouse capacity is measured in cubic meters, so `sku_bulk_pack` consumes more space than `sku_standard`.

## Run

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload
```

Docs are available at:

```text
http://127.0.0.1:8000/docs
```

## Core Endpoints

- `GET /state`
- `GET /graph`
- `GET /kpis`
- `GET /actions/history`
- `GET /events/history`
- `GET /alerts/history`
- `POST /tick`
- `POST /reset`
- `POST /simulation/start`
- `POST /simulation/stop`
- `GET /simulation/status`

Simulation endpoints deep-copy state and do not mutate the real world:

- `POST /simulate/transfer-inventory`
- `POST /simulate/update-production-schedule`
- `POST /simulate/update-supplier-allocation`
- `POST /simulate/update-reorder-point`

Execute endpoints mutate state and append action history:

- `POST /execute/transfer-inventory`
- `POST /execute/update-production-schedule`
- `POST /execute/update-lane`
- `POST /execute/update-supplier-allocation`
- `POST /execute/update-reorder-point`

Supplier allocation and reorder point endpoints are preserved for API compatibility, but currently return clear validation errors in the industrial model.

## Example Transfer Simulation

```bash
curl -X POST http://127.0.0.1:8000/simulate/transfer-inventory \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "sku_standard",
    "from_node": "chicago_hub",
    "to_node": "west_coast_dc",
    "units": 500,
    "lane_id": "chicago_to_west_rail",
    "weeks_to_simulate": 1
  }'
```

The response includes before/after KPIs, KPI deltas, constraint violations, a tradeoff summary, and a state preview.

## Example Production Schedule Simulation

```bash
curl -X POST http://127.0.0.1:8000/simulate/update-production-schedule \
  -H "Content-Type: application/json" \
  -d '{
    "production_node_id": "central_factory",
    "new_product_id": "sku_bulk_pack",
    "weeks_to_simulate": 2
  }'
```

This exposes setup fees, changeover delay, production output loss, service effects, and financial consequences. The backend does not decide whether the switch is good.

## Agent Loop

Agents should:

1. Observe `GET /state`, `GET /graph`, `GET /kpis`, and `GET /alerts/history`.
2. Propose candidate actions externally.
3. Use `/simulate/...` endpoints to compare consequences.
4. Execute approved actions with `/execute/...`.
5. Advance time with `/tick` or `/simulation/start`.
6. Audit outcomes through histories and KPIs.

No endpoint chooses the best action.
