from datetime import datetime, timezone
import random
from uuid import uuid4

from simulation.inventory_utils import add_inventory, age_inventory_one_week, remove_inventory_fifo
from simulation.kpi_engine import calculate_kpis


def _timestamp():
    return datetime.now(timezone.utc).isoformat()


def _log_event(state, event_type, message, impact=None):
    entry = {
        "timestamp": _timestamp(),
        "time_step": state["time_step"],
        "virtual_week": state["virtual_week"],
        "event_type": event_type,
        "message": message,
        "impact": impact or {},
    }
    state["event_history"].append(entry)
    return entry


def _rng_for_tick(state):
    seed = state.get("random_seed")
    return random.Random() if seed is None else random.Random(seed + state["virtual_week"] * 9973)


def _create_shipment(state, product_id, from_node, to_node, units, lane_id):
    lane = state["lanes"][lane_id]
    transit_weeks = lane["transit_weeks"] + lane.get("current_delay_weeks", 0)
    cost = units * lane["cost_per_unit"]
    emissions = units * lane["emissions_per_unit"]
    state["current_week_transport_cost"] += cost
    state["current_week_emissions"] += emissions
    if transit_weeks <= 0:
        add_inventory(state, to_node, product_id, units, age_weeks=0)
        return None
    shipment = {
        "shipment_id": str(uuid4()),
        "product_id": product_id,
        "from_node": from_node,
        "to_node": to_node,
        "units": units,
        "mode": lane["mode"],
        "lane_id": lane_id,
        "created_week": state["virtual_week"],
        "arrival_week": state["virtual_week"] + transit_weeks,
        "cost": round(cost, 2),
        "emissions": round(emissions, 2),
    }
    state["in_transit_shipments"].append(shipment)
    return shipment


def process_arrivals(state):
    arrived = []
    pending = []
    for shipment in state.get("in_transit_shipments", []):
        if shipment["arrival_week"] <= state["virtual_week"]:
            add_inventory(state, shipment["to_node"], shipment["product_id"], shipment["units"], age_weeks=0)
            arrived.append(shipment)
            _log_event(
                state,
                "shipment_arrival",
                f"Shipment arrived: {shipment['units']} {shipment['product_id']} from {shipment['from_node']} to {shipment['to_node']} by {shipment['mode']}.",
                {"shipment_id": shipment["shipment_id"], "lane_id": shipment["lane_id"]},
            )
        else:
            pending.append(shipment)
    state["in_transit_shipments"] = pending
    return arrived


def _process_production(state):
    results = {}
    for node_id in ["central_factory", "co_packer_plant"]:
        node = state["nodes"][node_id]
        product_id = node["active_product_id"]
        if node["current_changeover_remaining_weeks"] > 0:
            node["current_changeover_remaining_weeks"] -= 1
            results[node_id] = {"product_id": product_id, "units_produced": 0, "status": "changeover"}
            _log_event(state, "production_blocked", f"{node_id} produced 0 units due to changeover.", {"node_id": node_id})
            continue

        units = node["weekly_capacity_units"]
        production_cost = units * node["production_cost_per_unit"][product_id]
        state["current_week_production_cost"] += production_cost
        lane_id = state["production_routing"][node_id]
        lane = state["lanes"][lane_id]
        shipment = _create_shipment(state, product_id, node_id, lane["destination"], units, lane_id)
        results[node_id] = {
            "product_id": product_id,
            "units_produced": units,
            "production_cost": round(production_cost, 2),
            "routed_via": lane_id,
            "shipment_id": shipment["shipment_id"] if shipment else None,
        }
        _log_event(state, "production_output", f"{node_id} produced {units} units of {product_id}.", results[node_id])
    return results


def _recalculate_demand(state, rng):
    demand = {}
    for channel_id, channel in state["demand_channels"].items():
        demand[channel_id] = {}
        for product_id, baseline in channel["baseline_weekly_demand"].items():
            noise = rng.uniform(-channel["volatility"], channel["volatility"])
            units = max(0, int(baseline * channel["seasonality_factor"] * (1 + noise)))
            channel["current_weekly_demand"][product_id] = units
            demand[channel_id][product_id] = units
    _log_event(state, "demand_drift", "Demand recalculated for all channels and SKUs.", demand)
    return demand


def _fulfill_demand(state):
    unmet = {}
    fulfilled = {}
    for channel_id, channel in state["demand_channels"].items():
        node_id = channel["served_by"]
        unmet[channel_id] = {}
        fulfilled[channel_id] = {}
        for product_id, demand in channel["current_weekly_demand"].items():
            available = sum(bucket["units"] for bucket in state["nodes"][node_id].get("inventory", {}).get(product_id, []))
            served = min(available, demand)
            if served:
                remove_inventory_fifo(state, node_id, product_id, served)
            shortage = demand - served
            fulfilled[channel_id][product_id] = served
            unmet[channel_id][product_id] = shortage
    state["last_unmet_demand"] = unmet
    state["last_fulfilled_demand"] = fulfilled
    state["last_demand_fulfilled_time_step"] = state["time_step"]
    state["service_projection_dirty"] = False
    _log_event(state, "demand_fulfillment", "Demand fulfilled from assigned distribution nodes.", {"fulfilled": fulfilled, "unmet": unmet})
    return {"fulfilled": fulfilled, "unmet": unmet}


def _inject_disruptions(state, rng):
    events = []
    if rng.random() < 0.15:
        channel_id, product_id, multiplier = rng.choice([
            ("direct_to_consumer", "sku_standard", 1.30),
            ("big_box_retail", "sku_bulk_pack", 1.25),
        ])
        current = state["demand_channels"][channel_id]["current_weekly_demand"][product_id]
        adjusted = int(current * multiplier)
        state["demand_channels"][channel_id]["current_weekly_demand"][product_id] = adjusted
        events.append(_log_event(state, "demand_spike", f"{channel_id} {product_id} demand spiked to {adjusted}.", {"channel_id": channel_id, "product_id": product_id, "multiplier": multiplier}))
    if rng.random() < 0.10:
        lane_id = rng.choice(["cocoa_to_factory_ocean", "factory_to_chicago_rail"])
        lane = state["lanes"][lane_id]
        lane["current_delay_weeks"] = min(3, lane["current_delay_weeks"] + 1)
        events.append(_log_event(state, "lane_delay", f"{lane_id} delayed by one additional week.", {"lane_id": lane_id, "current_delay_weeks": lane["current_delay_weeks"]}))
    else:
        for lane_id in ["cocoa_to_factory_ocean", "factory_to_chicago_rail"]:
            state["lanes"][lane_id]["current_delay_weeks"] = max(0, state["lanes"][lane_id]["current_delay_weeks"] - 1)
    if rng.random() < 0.08:
        node = state["nodes"]["import_cocoa_port"]
        node["reliability"] = max(0.75, node["reliability"] - 0.03)
        events.append(_log_event(state, "supplier_reliability_dip", "import_cocoa_port reliability dipped.", {"reliability": round(node["reliability"], 3)}))
    if rng.random() < 0.08:
        lane = state["lanes"]["emergency_air_chicago_to_west"]
        lane["cost_per_unit"] = round(min(5.50, lane["cost_per_unit"] * 1.15), 2)
        events.append(_log_event(state, "air_cost_spike", "Emergency air freight cost increased.", {"cost_per_unit": lane["cost_per_unit"]}))
    if rng.random() < 0.10:
        for channel in state["demand_channels"].values():
            for product_id, current in channel["current_weekly_demand"].items():
                channel["current_weekly_demand"][product_id] = int(current * 0.82)
        events.append(_log_event(state, "demand_slump", "Demand slump reduced all channel demand.", {"multiplier": 0.82}))
    return events[:2]


def _record_alerts(state, kpis):
    added = []
    for alert in kpis["alerts"]:
        if alert["severity"] in {"warning", "critical"}:
            entry = {"timestamp": _timestamp(), "time_step": state["time_step"], "virtual_week": state["virtual_week"], **alert}
            state["alert_history"].append(entry)
            added.append(entry)
    return added


def apply_tick(state):
    state["time_step"] += 1
    state["virtual_week"] += 1
    state["current_week_transport_cost"] = 0.0
    state["current_week_emissions"] = 0.0
    state["current_week_production_cost"] = 0.0
    state["current_week_changeover_cost"] = 0.0

    rng = _rng_for_tick(state)
    wastage = age_inventory_one_week(state)
    state["current_week_wastage_cost"] = wastage["wastage_cost"]
    if wastage["wastage_cost"] > 0:
        _log_event(state, "inventory_expired", "Expired inventory was removed.", wastage)

    arrived_shipments = process_arrivals(state)
    production = _process_production(state)
    demand = _recalculate_demand(state, rng)
    disruption_events = _inject_disruptions(state, rng)
    demand_result = _fulfill_demand(state)

    kpis = calculate_kpis(state)
    state["kpis"] = kpis
    _record_alerts(state, kpis)

    return {
        "time_step": state["time_step"],
        "virtual_week": state["virtual_week"],
        "events": state["event_history"][-10:] + disruption_events,
        "arrived_shipments": arrived_shipments,
        "wastage": wastage,
        "production": production,
        "demand": {"current": demand, **demand_result},
        "kpis": kpis,
        "state": state,
    }
