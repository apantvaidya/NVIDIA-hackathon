from typing import Dict, Optional

from pydantic import BaseModel, model_validator


class TransferInventoryRequest(BaseModel):
    product_id: str
    from_node: Optional[str] = None
    to_node: Optional[str] = None
    units: int
    lane_id: Optional[str] = None
    mode: Optional[str] = None
    weeks_to_simulate: Optional[int] = 0
    # Backward-compatible aliases for older callers.
    from_warehouse: Optional[str] = None
    to_warehouse: Optional[str] = None

    @model_validator(mode="after")
    def fill_legacy_node_fields(self):
        if self.from_node is None:
            self.from_node = self.from_warehouse
        if self.to_node is None:
            self.to_node = self.to_warehouse
        if self.from_node is None or self.to_node is None:
            raise ValueError("from_node and to_node are required.")
        return self


class SupplierAllocationRequest(BaseModel):
    allocations: Dict[str, float]


class ReorderPointRequest(BaseModel):
    warehouse_id: str
    product_id: str
    new_reorder_point: int


class LaneUpdateRequest(BaseModel):
    lane_id: str
    status: Optional[str] = None
    transit_weeks: Optional[int] = None
    transit_days: Optional[int] = None
    capacity: Optional[int] = None


class ProductionScheduleRequest(BaseModel):
    production_node_id: str
    new_product_id: str
    weeks_to_simulate: Optional[int] = 0
