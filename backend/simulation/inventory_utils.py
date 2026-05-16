def _inventory_for_node(state, node_id):
    if node_id not in state["nodes"]:
        raise ValueError(f"Unknown node: {node_id}")
    return state["nodes"][node_id].setdefault("inventory", {})


def _product_buckets(state, node_id, product_id):
    if product_id not in state["products"]:
        raise ValueError(f"Unknown product: {product_id}")
    return _inventory_for_node(state, node_id).setdefault(product_id, [])


def get_total_inventory(state, node_id, product_id):
    return sum(bucket["units"] for bucket in _product_buckets(state, node_id, product_id))


def get_total_inventory_volume(state, node_id):
    inventory = _inventory_for_node(state, node_id)
    total_volume = 0.0
    for product_id, buckets in inventory.items():
        unit_volume = state["products"][product_id]["volume_cubic_meters_per_unit"]
        total_volume += sum(bucket["units"] * unit_volume for bucket in buckets)
    return total_volume


def add_inventory(state, node_id, product_id, units, age_weeks=0):
    if units < 0:
        raise ValueError("Inventory units to add cannot be negative.")
    if units == 0:
        return

    buckets = _product_buckets(state, node_id, product_id)
    for bucket in buckets:
        if bucket["age_weeks"] == age_weeks:
            bucket["units"] += units
            break
    else:
        buckets.append({"age_weeks": age_weeks, "units": units})
    buckets.sort(key=lambda bucket: bucket["age_weeks"], reverse=True)


def remove_inventory_fifo(state, node_id, product_id, units):
    if units <= 0:
        raise ValueError("Inventory units to remove must be positive.")
    total_inventory = get_total_inventory(state, node_id, product_id)
    if total_inventory < units:
        raise ValueError(f"Node {node_id} only has {total_inventory} units of {product_id}.")

    buckets = _product_buckets(state, node_id, product_id)
    buckets.sort(key=lambda bucket: bucket["age_weeks"], reverse=True)
    remaining = units
    removed_units = 0

    for bucket in list(buckets):
        if remaining <= 0:
            break
        removed = min(bucket["units"], remaining)
        bucket["units"] -= removed
        removed_units += removed
        remaining -= removed

    _inventory_for_node(state, node_id)[product_id] = [
        bucket for bucket in buckets if bucket["units"] > 0
    ]
    return removed_units


def age_inventory_one_week(state):
    expired_units_by_node = {}
    expired_units_by_product = {product_id: 0 for product_id in state["products"]}
    wastage_cost = 0.0

    for node_id, node in state["nodes"].items():
        inventory = node.get("inventory")
        if not inventory:
            continue
        expired_units_by_node[node_id] = {}
        for product_id, buckets in inventory.items():
            shelf_life = state["products"][product_id]["shelf_life_weeks"]
            unit_wastage_cost = state["products"][product_id]["wastage_cost_per_unit"]
            kept_buckets = []
            expired_units = 0
            for bucket in buckets:
                aged_bucket = {"age_weeks": bucket["age_weeks"] + 1, "units": bucket["units"]}
                if aged_bucket["age_weeks"] > shelf_life:
                    expired_units += aged_bucket["units"]
                else:
                    kept_buckets.append(aged_bucket)
            inventory[product_id] = kept_buckets
            expired_units_by_node[node_id][product_id] = expired_units
            expired_units_by_product[product_id] += expired_units
            wastage_cost += expired_units * unit_wastage_cost

    return {
        "expired_units_by_node": expired_units_by_node,
        "expired_units_by_product": expired_units_by_product,
        "wastage_cost": round(wastage_cost, 2),
    }


def get_units_near_expiration(state, node_id, product_id, threshold_weeks=4):
    buckets = _product_buckets(state, node_id, product_id)
    shelf_life = state["products"][product_id]["shelf_life_weeks"]
    near_expiration_age = max(0, shelf_life - threshold_weeks)
    return sum(bucket["units"] for bucket in buckets if bucket["age_weeks"] >= near_expiration_age)


def get_inventory_age_summary(state, node_id, product_id):
    buckets = _product_buckets(state, node_id, product_id)
    total_units = sum(bucket["units"] for bucket in buckets)
    if not buckets:
        return {"total_units": 0, "oldest_age": 0, "youngest_age": 0, "units_near_expiration": 0}

    ages = [bucket["age_weeks"] for bucket in buckets]
    return {
        "total_units": total_units,
        "oldest_age": max(ages),
        "youngest_age": min(ages),
        "units_near_expiration": get_units_near_expiration(state, node_id, product_id),
    }
