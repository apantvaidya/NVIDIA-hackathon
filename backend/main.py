import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent_orchestration.router import router as agent_router
from simulation.action_engine import (
    transfer_inventory,
    update_lane_status,
    update_production_schedule,
    update_reorder_point,
    update_supplier_allocation,
)
from simulation.event_engine import apply_tick
from simulation.inventory_utils import get_total_inventory_volume
from simulation.kpi_engine import calculate_kpis
from simulation.scenario_engine import (
    simulate_reorder_point,
    simulate_supplier_allocation,
    simulate_transfer_inventory,
    simulate_update_production_schedule,
)
from simulation.schemas import (
    LaneUpdateRequest,
    ProductionScheduleRequest,
    ReorderPointRequest,
    SupplierAllocationRequest,
    TransferInventoryRequest,
)
from simulation.state import get_world_state, reset_world_state


app = FastAPI(title="ChainPilot Simulation Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://0.0.0.0:5173",
        "*",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
SIMULATION_TASK = None
app.include_router(agent_router, prefix="/api/agent", tags=["agent-orchestration"])


def _refresh_kpis(state):
    state["kpis"] = calculate_kpis(state)
    return state["kpis"]


def _execute_action(action_callback):
    state = get_world_state()
    try:
        log_entry = action_callback(state)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "success": True,
        "message": "Action executed and logged.",
        "log_entry": log_entry,
        "new_kpis": _refresh_kpis(state),
        "updated_state": state,
    }


def _graph_response(state):
    kpis = _refresh_kpis(state)
    nodes = []
    for node_id, node in state["nodes"].items():
        metrics = {}
        if node.get("node_type") == "distribution":
            metrics = {
                "inventory_volume": get_total_inventory_volume(state, node_id),
                "utilization": kpis["inventory"]["warehouse_utilization"].get(node_id, 0),
                "service_channels": node.get("service_channels", []),
            }
        elif node.get("node_type") == "production":
            metrics = {
                "active_product_id": node["active_product_id"],
                "weekly_capacity_units": node["weekly_capacity_units"],
                "changeover_remaining_weeks": node["current_changeover_remaining_weeks"],
                "flexibility_score": node["flexibility_score"],
            }
        elif node.get("node_type") == "demand_channel":
            metrics = {
                "current_weekly_demand": state["demand_channels"].get(node_id, {}).get("current_weekly_demand", {}),
                "stockout_risk": kpis["service"]["stockout_risk"].get(node_id, 0),
            }
        else:
            metrics = {
                "reliability": node.get("reliability"),
                "lead_time_variance": node.get("lead_time_variance"),
            }
        nodes.append({
            "id": node_id,
            "label": node["name"],
            "type": node["node_type"],
            "tier": node["tier"],
            "status": node.get("status", "active"),
            "description": node.get("description"),
            "operational_notes": node.get("operational_notes"),
            "risk_factors": node.get("risk_factors", []),
            "metrics": metrics,
        })

    edges = []
    for lane_id, lane in state["lanes"].items():
        edges.append({
            "id": lane_id,
            "source": lane["origin"],
            "target": lane["destination"],
            "mode": lane["mode"],
            "status": lane["status"],
            "cost_per_unit": lane["cost_per_unit"],
            "transit_weeks": lane["transit_weeks"],
            "capacity_units_per_week": lane["capacity_units_per_week"],
            "emissions_per_unit": lane["emissions_per_unit"],
            "reliability": lane["reliability"],
            "current_delay_weeks": lane["current_delay_weeks"],
        })
    return {"nodes": nodes, "edges": edges}


async def _background_tick_loop():
    get_world_state()["simulation_status"] = "running"
    try:
        while get_world_state()["simulation_status"] == "running":
            await asyncio.sleep(15)
            apply_tick(get_world_state())
    except asyncio.CancelledError:
        get_world_state()["simulation_status"] = "stopped"
        raise


@app.get("/")
def root():
    return {"service": "ChainPilot Simulation Backend", "status": "ok"}


@app.get("/state")
def state():
    state = get_world_state()
    _refresh_kpis(state)
    return state


@app.get("/kpis")
def kpis():
    return _refresh_kpis(get_world_state())


@app.get("/graph")
def graph():
    return _graph_response(get_world_state())


@app.get("/actions/history")
def action_history():
    return get_world_state()["action_history"]


@app.get("/events/history")
def event_history():
    return get_world_state()["event_history"]


@app.get("/alerts/history")
def alert_history():
    return get_world_state()["alert_history"]


@app.post("/simulate/transfer-inventory")
def simulate_transfer_inventory_endpoint(request: TransferInventoryRequest):
    return simulate_transfer_inventory(
        get_world_state(),
        request.product_id,
        request.from_node,
        request.to_node,
        request.units,
        lane_id=request.lane_id,
        mode=request.mode,
        weeks_to_simulate=request.weeks_to_simulate or 0,
    )


@app.post("/execute/transfer-inventory")
def execute_transfer_inventory(request: TransferInventoryRequest):
    return _execute_action(
        lambda state: transfer_inventory(
            state,
            request.product_id,
            request.from_node,
            request.to_node,
            request.units,
            lane_id=request.lane_id,
            mode=request.mode,
        )
    )


@app.post("/simulate/update-production-schedule")
def simulate_production_schedule(request: ProductionScheduleRequest):
    return simulate_update_production_schedule(
        get_world_state(),
        request.production_node_id,
        request.new_product_id,
        request.weeks_to_simulate or 0,
    )


@app.post("/execute/update-production-schedule")
def execute_production_schedule(request: ProductionScheduleRequest):
    return _execute_action(
        lambda state: update_production_schedule(
            state, request.production_node_id, request.new_product_id
        )
    )


@app.post("/simulate/update-supplier-allocation")
def simulate_update_supplier_allocation(request: SupplierAllocationRequest):
    return simulate_supplier_allocation(get_world_state(), request.allocations)


@app.post("/execute/update-supplier-allocation")
def execute_update_supplier_allocation(request: SupplierAllocationRequest):
    return _execute_action(lambda state: update_supplier_allocation(state, request.allocations))


@app.post("/simulate/update-reorder-point")
def simulate_update_reorder_point(request: ReorderPointRequest):
    return simulate_reorder_point(
        get_world_state(), request.warehouse_id, request.product_id, request.new_reorder_point
    )


@app.post("/execute/update-reorder-point")
def execute_update_reorder_point(request: ReorderPointRequest):
    return _execute_action(
        lambda state: update_reorder_point(
            state, request.warehouse_id, request.product_id, request.new_reorder_point
        )
    )


@app.post("/execute/update-lane")
def execute_update_lane(request: LaneUpdateRequest):
    return _execute_action(
        lambda state: update_lane_status(
            state,
            request.lane_id,
            request.status,
            request.transit_weeks,
            request.capacity,
            transit_days=request.transit_days,
        )
    )


@app.post("/tick")
def tick():
    return apply_tick(get_world_state())


@app.post("/reset")
def reset():
    state = reset_world_state()
    return {"success": True, "message": "World state reset to industrial equilibrium.", "state": state, "kpis": _refresh_kpis(state)}


@app.post("/simulation/start")
async def simulation_start():
    global SIMULATION_TASK
    state = get_world_state()
    if SIMULATION_TASK and not SIMULATION_TASK.done():
        return {"success": True, "message": "Simulation loop is already running.", "simulation_status": state["simulation_status"], "virtual_week": state["virtual_week"], "time_step": state["time_step"]}
    state["simulation_status"] = "running"
    SIMULATION_TASK = asyncio.create_task(_background_tick_loop())
    return {"success": True, "message": "Background simulation loop started.", "simulation_status": state["simulation_status"], "virtual_week": state["virtual_week"], "time_step": state["time_step"]}


@app.post("/simulation/stop")
async def simulation_stop():
    global SIMULATION_TASK
    state = get_world_state()
    state["simulation_status"] = "stopped"
    if SIMULATION_TASK and not SIMULATION_TASK.done():
        SIMULATION_TASK.cancel()
        try:
            await SIMULATION_TASK
        except asyncio.CancelledError:
            pass
    SIMULATION_TASK = None
    return {"success": True, "message": "Background simulation loop stopped.", "simulation_status": state["simulation_status"], "virtual_week": state["virtual_week"], "time_step": state["time_step"]}


@app.get("/simulation/status")
def simulation_status():
    state = get_world_state()
    running = bool(SIMULATION_TASK and not SIMULATION_TASK.done())
    return {
        "simulation_status": "running" if running else state["simulation_status"],
        "virtual_week": state["virtual_week"],
        "time_step": state["time_step"],
    }
