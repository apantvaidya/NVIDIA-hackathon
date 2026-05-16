from simulation.inventory_utils import (
    get_total_inventory,
    get_total_inventory_volume,
    get_units_near_expiration,
)


DISTRIBUTION_NODES = ["chicago_hub", "west_coast_dc"]
PRODUCTION_NODES = ["central_factory", "co_packer_plant"]


def _round_dict(values, digits=4):
    return {key: round(value, digits) for key, value in values.items()}


def _demand_totals(state):
    totals = {product_id: 0 for product_id in state["products"]}
    for channel in state["demand_channels"].values():
        for product_id, units in channel["current_weekly_demand"].items():
            totals[product_id] += units
    return totals


def _projected_unmet(state):
    unmet = {}
    fulfilled = {}
    for channel_id, channel in state["demand_channels"].items():
        served_by = channel["served_by"]
        unmet[channel_id] = {}
        fulfilled[channel_id] = {}
        for product_id, demand in channel["current_weekly_demand"].items():
            available = get_total_inventory(state, served_by, product_id)
            shortage = max(0, demand - available)
            unmet[channel_id][product_id] = shortage
            fulfilled[channel_id][product_id] = max(0, demand - shortage)
    return unmet, fulfilled


def _mode_shares(state):
    mode_units = {"air": 0, "truck": 0, "rail": 0, "ocean": 0, "local": 0}
    for shipment in state.get("in_transit_shipments", []):
        mode_units[shipment["mode"]] = mode_units.get(shipment["mode"], 0) + shipment["units"]
    for action in state.get("action_history", []):
        if action["time_step"] == state["time_step"] and action["action_type"] == "transfer_inventory":
            mode = action["payload"].get("mode")
            mode_units[mode] = mode_units.get(mode, 0) + action["payload"].get("units", 0)

    total_units = sum(mode_units.values())
    if total_units == 0:
        return {mode: 0 for mode in ["air", "truck", "rail", "ocean"]}
    return {mode: mode_units.get(mode, 0) / total_units for mode in ["air", "truck", "rail", "ocean"]}


def calculate_kpis(state):
    projected_unmet, projected_fulfilled = _projected_unmet(state)
    unmet = state.get("last_unmet_demand") or projected_unmet
    fulfilled = state.get("last_fulfilled_demand") or projected_fulfilled

    demand_totals = _demand_totals(state)
    total_demand_units = sum(demand_totals.values())

    estimated_revenue = 0.0
    stockout_penalty = 0.0
    vendor_compliance_fines = 0.0
    stockout_risk = {}
    service_level_estimate = {}

    for channel_id, channel in state["demand_channels"].items():
        channel_demand = sum(channel["current_weekly_demand"].values())
        channel_unmet = sum(unmet.get(channel_id, {}).values())
        stockout_risk[channel_id] = 0 if channel_demand == 0 else channel_unmet / channel_demand
        service_level_estimate[channel_id] = max(0, 1 - stockout_risk[channel_id])
        for product_id, served_units in fulfilled.get(channel_id, {}).items():
            estimated_revenue += served_units * state["products"][product_id]["margin_per_unit"]
        for product_id, shortage in unmet.get(channel_id, {}).items():
            product = state["products"][product_id]
            stockout_penalty += shortage * product["stockout_cost_per_unit"]
            if channel_id == "big_box_retail" and shortage > 0:
                retail_value = product.get(
                    "estimated_retail_value_per_unit",
                    product["margin_per_unit"] + product["stockout_cost_per_unit"],
                )
                vendor_compliance_fines += shortage * retail_value * channel["chargeback_rate"]

    supplier_cost = 0.0
    supplier_risk_index = 0.0
    lead_time_uncertainty_index = 0.0
    sourcing_nodes = [node for node in state["nodes"].values() if node["node_type"] == "sourcing"]
    for node in sourcing_nodes:
        share = 1 / len(sourcing_nodes)
        supplier_cost += total_demand_units * share * node["costs"]["cost_per_unit"]
        supplier_risk_index += share * (1 - node["reliability"])
        lead_time_uncertainty_index += share * node["lead_time_variance"]

    total_inventory_units = {}
    total_inventory_volume = {}
    warehouse_utilization = {}
    excess_inventory = {}
    units_near_expiration = {}
    holding_cost = 0.0

    for node_id in DISTRIBUTION_NODES:
        node = state["nodes"][node_id]
        volume = get_total_inventory_volume(state, node_id)
        total_inventory_volume[node_id] = round(volume, 2)
        warehouse_utilization[node_id] = volume / node["capacity_cubic_meters"]
        total_units = 0
        near_expiration = 0
        served_demand = 0
        for product_id, product in state["products"].items():
            units = get_total_inventory(state, node_id, product_id)
            total_units += units
            near_expiration += get_units_near_expiration(state, node_id, product_id)
            holding_cost += (
                units
                * product["volume_cubic_meters_per_unit"]
                * product["holding_cost_per_cubic_meter_per_week"]
                * node["holding_cost_modifier"]
            )
        for channel_id in node.get("service_channels", []):
            served_demand += sum(state["demand_channels"][channel_id]["current_weekly_demand"].values())
        total_inventory_units[node_id] = total_units
        excess_inventory[node_id] = max(0, total_units - served_demand)
        units_near_expiration[node_id] = near_expiration

    transport_cost = state.get("current_week_transport_cost", 0.0)
    emissions = state.get("current_week_emissions", 0.0)
    production_cost = state.get("current_week_production_cost", 0.0)
    changeover_cost = state.get("current_week_changeover_cost", 0.0)
    wastage_cost = state.get("current_week_wastage_cost", 0.0)
    estimated_profit = (
        estimated_revenue
        - supplier_cost
        - production_cost
        - transport_cost
        - holding_cost
        - stockout_penalty
        - vendor_compliance_fines
        - changeover_cost
        - wastage_cost
    )
    gross_margin_per_unit_estimate = 0 if total_demand_units == 0 else estimated_profit / total_demand_units

    mode_shares = _mode_shares(state)
    total_in_transit_units = sum(shipment["units"] for shipment in state.get("in_transit_shipments", []))
    if total_in_transit_units:
        avg_speed = sum(
            shipment["units"] * max(0, shipment["arrival_week"] - state["virtual_week"])
            for shipment in state["in_transit_shipments"]
        ) / total_in_transit_units
    else:
        avg_speed = 0.0

    active_schedules = {}
    changeover_remaining = {}
    available_capacity = {}
    for node_id in PRODUCTION_NODES:
        node = state["nodes"][node_id]
        active_schedules[node_id] = node["active_product_id"]
        remaining = node["current_changeover_remaining_weeks"]
        changeover_remaining[node_id] = remaining
        available_capacity[node_id] = 0 if remaining > 0 else node["weekly_capacity_units"]

    alerts = []
    for channel_id, risk in stockout_risk.items():
        if risk > 0.20:
            alerts.append({"severity": "critical" if risk > 0.50 else "warning", "type": "stockout_risk", "message": f"{channel_id} stockout risk is {risk:.0%}."})
    if sum(unmet.get("big_box_retail", {}).values()) > 0:
        alerts.append({"severity": "warning", "type": "big_box_unmet_demand", "message": "big_box_retail has unmet demand and may issue chargebacks."})
    if vendor_compliance_fines > 0:
        alerts.append({"severity": "critical" if vendor_compliance_fines > 5000 else "warning", "type": "vendor_compliance_fines", "message": f"Vendor compliance fines are estimated at {vendor_compliance_fines:.2f}."})
    for node_id, utilization in warehouse_utilization.items():
        if utilization > 0.90:
            alerts.append({"severity": "critical" if utilization > 0.95 else "warning", "type": "warehouse_utilization", "message": f"{node_id} utilization is {utilization:.0%}."})
    for node_id, units in units_near_expiration.items():
        if units > 500:
            alerts.append({"severity": "warning", "type": "near_expiration", "message": f"{node_id} has {units} units near expiration."})
    if supplier_risk_index > 0.08:
        alerts.append({"severity": "warning", "type": "supplier_risk", "message": f"Supplier risk index is {supplier_risk_index:.3f}."})
    if emissions > 1200:
        alerts.append({"severity": "warning", "type": "emissions", "message": f"Estimated weekly emissions are {emissions:.1f}."})
    if estimated_profit < 5000:
        alerts.append({"severity": "critical", "type": "profit", "message": f"Estimated profit is low at {estimated_profit:.2f}."})
    for node_id, remaining in changeover_remaining.items():
        if remaining > 0:
            alerts.append({"severity": "warning", "type": "production_changeover", "message": f"{node_id} is in changeover for {remaining} more week(s)."})
    for lane_id, lane in state["lanes"].items():
        if lane.get("current_delay_weeks", 0) > 0:
            alerts.append({"severity": "warning", "type": "lane_delay", "message": f"{lane_id} has {lane['current_delay_weeks']} active delay week(s)."})

    return {
        "virtual_week": state["virtual_week"],
        "financial": {
            "estimated_revenue": round(estimated_revenue, 2),
            "supplier_cost": round(supplier_cost, 2),
            "production_cost": round(production_cost, 2),
            "transport_cost": round(transport_cost, 2),
            "holding_cost": round(holding_cost, 2),
            "stockout_penalty": round(stockout_penalty, 2),
            "vendor_compliance_fines": round(vendor_compliance_fines, 2),
            "changeover_cost": round(changeover_cost, 2),
            "wastage_cost": round(wastage_cost, 2),
            "estimated_profit": round(estimated_profit, 2),
            "gross_margin_per_unit_estimate": round(gross_margin_per_unit_estimate, 4),
        },
        "service": {
            "stockout_risk": _round_dict(stockout_risk),
            "service_level_estimate": _round_dict(service_level_estimate),
            "unmet_demand_units": unmet,
        },
        "inventory": {
            "total_inventory_units": total_inventory_units,
            "total_inventory_volume": total_inventory_volume,
            "warehouse_utilization": _round_dict(warehouse_utilization),
            "excess_inventory": excess_inventory,
            "units_near_expiration": units_near_expiration,
        },
        "logistics": {
            "estimated_transport_cost": round(transport_cost, 2),
            "estimated_emissions": round(emissions, 2),
            "average_delivery_speed_weeks": round(avg_speed, 2),
            "air_freight_share": round(mode_shares["air"], 4),
            "truck_share": round(mode_shares["truck"], 4),
            "rail_share": round(mode_shares["rail"], 4),
            "ocean_share": round(mode_shares["ocean"], 4),
        },
        "production": {
            "active_schedules": active_schedules,
            "changeover_remaining_weeks": changeover_remaining,
            "available_capacity_units": available_capacity,
        },
        "sourcing": {
            "supplier_risk_index": round(supplier_risk_index, 4),
            "lead_time_uncertainty_index": round(lead_time_uncertainty_index, 4),
        },
        "alerts": alerts,
    }
