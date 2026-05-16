from copy import deepcopy

from simulation.action_engine import (
    transfer_inventory,
    update_production_schedule,
    update_reorder_point,
    update_supplier_allocation,
)
from simulation.event_engine import apply_tick
from simulation.kpi_engine import calculate_kpis


def calculate_delta(before, after):
    delta = {}
    for key, before_value in before.items():
        if key == "alerts" or key not in after:
            continue
        after_value = after[key]
        if isinstance(before_value, dict) and isinstance(after_value, dict):
            delta[key] = calculate_delta(before_value, after_value)
        elif isinstance(before_value, (int, float)) and isinstance(after_value, (int, float)):
            delta[key] = round(after_value - before_value, 4)
    return delta


def _flatten_numeric(prefix, value):
    if isinstance(value, dict):
        flattened = {}
        for key, nested in value.items():
            flattened.update(_flatten_numeric(f"{prefix}.{key}" if prefix else key, nested))
        return flattened
    if isinstance(value, (int, float)):
        return {prefix: value}
    return {}


def _tradeoff_summary(before_kpis, after_kpis):
    before_flat = _flatten_numeric("", before_kpis)
    after_flat = _flatten_numeric("", after_kpis)
    improves = []
    worsens = []
    neutral = []
    lower_is_better = (
        "cost",
        "penalty",
        "fines",
        "risk",
        "unmet",
        "utilization",
        "emissions",
        "changeover_remaining",
        "wastage",
    )
    for metric, before_value in before_flat.items():
        if metric not in after_flat:
            continue
        diff = round(after_flat[metric] - before_value, 4)
        if abs(diff) < 0.0001:
            neutral.append(metric)
            continue
        is_lower_better = any(token in metric for token in lower_is_better)
        if (is_lower_better and diff < 0) or (not is_lower_better and diff > 0):
            improves.append(metric)
        else:
            worsens.append(metric)
    return {"improves": improves[:12], "worsens": worsens[:12], "neutral": neutral[:12]}


def _simulate(state, action_type, request, action_callback, weeks_to_simulate=0):
    preview = deepcopy(state)
    before_kpis = calculate_kpis(preview)
    constraint_violations = []
    try:
        action_callback(preview)
        action_costs = {
            "current_week_transport_cost": preview.get("current_week_transport_cost", 0.0),
            "current_week_emissions": preview.get("current_week_emissions", 0.0),
            "current_week_changeover_cost": preview.get("current_week_changeover_cost", 0.0),
            "current_week_production_cost": preview.get("current_week_production_cost", 0.0),
        }
        for _ in range(max(0, weeks_to_simulate or 0)):
            apply_tick(preview)
        if weeks_to_simulate:
            preview.update(action_costs)
        preview["action_history"] = deepcopy(state["action_history"])
        after_kpis = calculate_kpis(preview)
        preview["kpis"] = after_kpis
        return {
            "valid": True,
            "action_type": action_type,
            "request": request,
            "before_kpis": before_kpis,
            "after_kpis": after_kpis,
            "kpi_delta": calculate_delta(before_kpis, after_kpis),
            "constraint_violations": constraint_violations,
            "tradeoff_summary": _tradeoff_summary(before_kpis, after_kpis),
            "state_preview": preview,
        }
    except ValueError as error:
        constraint_violations.append(str(error))
        return {
            "valid": False,
            "action_type": action_type,
            "request": request,
            "before_kpis": before_kpis,
            "after_kpis": None,
            "kpi_delta": None,
            "constraint_violations": constraint_violations,
            "tradeoff_summary": {"improves": [], "worsens": [], "neutral": []},
            "state_preview": None,
        }


def simulate_transfer_inventory(state, product_id, from_node, to_node, units, lane_id=None, mode=None, weeks_to_simulate=0):
    request = {"product_id": product_id, "from_node": from_node, "to_node": to_node, "units": units, "lane_id": lane_id, "mode": mode, "weeks_to_simulate": weeks_to_simulate}
    return _simulate(
        state,
        "transfer_inventory",
        request,
        lambda preview: transfer_inventory(preview, product_id, from_node, to_node, units, lane_id=lane_id, mode=mode),
        weeks_to_simulate,
    )


def simulate_update_production_schedule(state, production_node_id, new_product_id, weeks_to_simulate=0):
    request = {"production_node_id": production_node_id, "new_product_id": new_product_id, "weeks_to_simulate": weeks_to_simulate}
    return _simulate(
        state,
        "update_production_schedule",
        request,
        lambda preview: update_production_schedule(preview, production_node_id, new_product_id),
        weeks_to_simulate,
    )


def simulate_supplier_allocation(state, allocations):
    return _simulate(state, "update_supplier_allocation", {"allocations": allocations}, lambda preview: update_supplier_allocation(preview, allocations))


def simulate_reorder_point(state, warehouse_id, product_id, new_reorder_point):
    request = {"warehouse_id": warehouse_id, "product_id": product_id, "new_reorder_point": new_reorder_point}
    return _simulate(state, "update_reorder_point", request, lambda preview: update_reorder_point(preview, warehouse_id, product_id, new_reorder_point))
