from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from simulation.inventory_utils import (
    add_inventory,
    get_total_inventory,
    get_total_inventory_volume,
    remove_inventory_fifo,
)


def _utc_timestamp():
    return datetime.now(timezone.utc).isoformat()


def log_action(state, action_type, payload, before, after):
    state["service_projection_dirty"] = True
    log_entry = {
        "timestamp": _utc_timestamp(),
        "time_step": state["time_step"],
        "virtual_week": state.get("virtual_week", 0),
        "action_type": action_type,
        "payload": payload,
        "before": before,
        "after": after,
    }
    state["action_history"].append(log_entry)
    return log_entry


def _require_node(state, node_id):
    if node_id not in state["nodes"]:
        raise ValueError(f"Unknown node: {node_id}")


def _require_product(state, product_id):
    if product_id not in state["products"]:
        raise ValueError(f"Unknown product: {product_id}")


def _find_lane(state, from_node, to_node, lane_id=None, mode=None):
    if lane_id:
        if lane_id not in state["lanes"]:
            raise ValueError(f"Unknown lane: {lane_id}")
        lane = state["lanes"][lane_id]
        if lane["origin"] != from_node or lane["destination"] != to_node:
            raise ValueError(f"Lane {lane_id} does not connect {from_node} to {to_node}.")
        if mode and lane["mode"] != mode:
            raise ValueError(f"Lane {lane_id} is mode {lane['mode']}, not {mode}.")
        return lane_id, lane

    matches = [
        (candidate_id, lane)
        for candidate_id, lane in state["lanes"].items()
        if lane["origin"] == from_node
        and lane["destination"] == to_node
        and (mode is None or lane["mode"] == mode)
    ]
    if not matches:
        suffix = f" with mode {mode}" if mode else ""
        raise ValueError(f"No lane connects {from_node} to {to_node}{suffix}.")
    return matches[0]


def _check_destination_capacity(state, to_node, product_id, units):
    node = state["nodes"][to_node]
    if "capacity_cubic_meters" not in node:
        return
    used_volume = get_total_inventory_volume(state, to_node)
    incoming_volume = 0.0
    for shipment in state.get("in_transit_shipments", []):
        if shipment["to_node"] == to_node:
            product = state["products"][shipment["product_id"]]
            incoming_volume += shipment["units"] * product["volume_cubic_meters_per_unit"]
    added_volume = units * state["products"][product_id]["volume_cubic_meters_per_unit"]
    utilization_limit = node["capacity_cubic_meters"] * state["constraints"]["max_warehouse_utilization"]
    if used_volume + incoming_volume + added_volume > utilization_limit:
        raise ValueError(f"Transfer would push {to_node} above warehouse utilization limit.")


def transfer_inventory(state, product_id, from_node, to_node, units, lane_id=None, mode=None):
    _require_product(state, product_id)
    _require_node(state, from_node)
    _require_node(state, to_node)
    if units <= 0:
        raise ValueError("Transfer units must be positive.")
    if units > state["constraints"]["max_auto_transfer_units"]:
        raise ValueError(
            f"Transfer exceeds max_auto_transfer_units of {state['constraints']['max_auto_transfer_units']}."
        )

    chosen_lane_id, lane = _find_lane(state, from_node, to_node, lane_id, mode)
    if lane["status"] != "active":
        raise ValueError(f"Lane {chosen_lane_id} is not active.")
    if units > lane["capacity_units_per_week"]:
        raise ValueError(f"Transfer exceeds lane capacity of {lane['capacity_units_per_week']}.")
    if get_total_inventory(state, from_node, product_id) < units:
        raise ValueError(f"Source node {from_node} does not have enough {product_id}.")
    _check_destination_capacity(state, to_node, product_id, units)

    before = {
        "source_inventory": deepcopy(state["nodes"][from_node].get("inventory", {})),
        "destination_inventory": deepcopy(state["nodes"][to_node].get("inventory", {})),
        "in_transit_count": len(state.get("in_transit_shipments", [])),
        "chosen_lane": chosen_lane_id,
        "mode": lane["mode"],
    }

    remove_inventory_fifo(state, from_node, product_id, units)
    transit_weeks = lane["transit_weeks"] + lane.get("current_delay_weeks", 0)
    arrival_week = state.get("virtual_week", 0) + transit_weeks
    cost = units * lane["cost_per_unit"]
    emissions = units * lane["emissions_per_unit"]
    state["current_week_transport_cost"] += cost
    state["current_week_emissions"] += emissions

    shipment = None
    if transit_weeks <= 0:
        add_inventory(state, to_node, product_id, units, age_weeks=0)
    else:
        shipment = {
            "shipment_id": str(uuid4()),
            "product_id": product_id,
            "from_node": from_node,
            "to_node": to_node,
            "units": units,
            "mode": lane["mode"],
            "lane_id": chosen_lane_id,
            "created_week": state.get("virtual_week", 0),
            "arrival_week": arrival_week,
            "cost": round(cost, 2),
            "emissions": round(emissions, 2),
        }
        state["in_transit_shipments"].append(shipment)

    after = {
        "source_inventory": deepcopy(state["nodes"][from_node].get("inventory", {})),
        "destination_inventory": deepcopy(state["nodes"][to_node].get("inventory", {})),
        "in_transit_count": len(state.get("in_transit_shipments", [])),
        "chosen_lane": chosen_lane_id,
        "mode": lane["mode"],
        "arrival_week": arrival_week,
        "shipment": shipment,
    }

    return log_action(
        state,
        "transfer_inventory",
        {
            "product_id": product_id,
            "from_node": from_node,
            "to_node": to_node,
            "units": units,
            "lane_id": chosen_lane_id,
            "mode": lane["mode"],
            "arrival_week": arrival_week,
            "cost": round(cost, 2),
            "emissions": round(emissions, 2),
        },
        before,
        after,
    )


def update_production_schedule(state, production_node_id, new_product_id):
    _require_node(state, production_node_id)
    _require_product(state, new_product_id)
    node = state["nodes"][production_node_id]
    if node["node_type"] != "production":
        raise ValueError(f"{production_node_id} is not a production node.")
    if new_product_id not in node["production_cost_per_unit"]:
        raise ValueError(f"{production_node_id} cannot produce {new_product_id}.")

    before = deepcopy(node)
    if node["active_product_id"] != new_product_id:
        node["active_product_id"] = new_product_id
        node["current_changeover_remaining_weeks"] = node["changeover_delay_weeks"]
        state["current_week_changeover_cost"] += node["changeover_setup_fee"]
    after = deepcopy(node)
    return log_action(
        state,
        "update_production_schedule",
        {"production_node_id": production_node_id, "new_product_id": new_product_id},
        before,
        after,
    )


def update_lane_status(state, lane_id, status=None, transit_weeks=None, capacity=None, transit_days=None):
    if lane_id not in state["lanes"]:
        raise ValueError(f"Unknown lane: {lane_id}")
    if transit_weeks is None and transit_days is not None:
        transit_weeks = max(0, round(transit_days / 7))
    if transit_weeks is not None and transit_weeks < 0:
        raise ValueError("transit_weeks cannot be negative.")
    if capacity is not None and capacity < 0:
        raise ValueError("capacity cannot be negative.")

    lane = state["lanes"][lane_id]
    before = deepcopy(lane)
    if status is not None:
        lane["status"] = status
    if transit_weeks is not None:
        lane["transit_weeks"] = transit_weeks
    if capacity is not None:
        lane["capacity_units_per_week"] = capacity
    after = deepcopy(lane)
    return log_action(state, "update_lane_status", {"lane_id": lane_id, "status": status, "transit_weeks": transit_weeks, "capacity": capacity}, before, after)


def update_supplier_allocation(state, allocations):
    raise ValueError("Supplier allocation actions are not supported in the industrial network model yet.")


def update_reorder_point(state, warehouse_id, product_id, new_reorder_point):
    raise ValueError("Reorder point actions are not supported in the industrial network model yet.")
