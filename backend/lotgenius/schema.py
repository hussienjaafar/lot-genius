from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ConditionEnum(str, Enum):
    New = "New"
    LikeNew = "LikeNew"
    UsedGood = "UsedGood"
    UsedFair = "UsedFair"
    Salvage = "Salvage"


class Item(BaseModel):
    sku_local: str | None = Field(default=None)
    title: str
    brand: str | None = None
    model: str | None = None
    asin: str | None = None
    upc: str | None = None
    ean: str | None = None
    upc_ean_asin: str | None = None
    condition: ConditionEnum | None = None
    quantity: int = 1
    est_cost_per_unit: float | None = None
    notes: str | None = None
    category_hint: str | None = None
    msrp: float | None = None
    color_size_variant: str | None = None
    lot_id: str | None = None

    @field_validator("quantity")
    @classmethod
    def _qty_positive(cls, v: int) -> int:
        if v is None:
            return 1
        if v <= 0:
            raise ValueError("quantity must be > 0")
        return v


def item_jsonschema() -> dict:
    """Return JSON Schema for Item (for UI contracts / validators)."""
    return Item.model_json_schema()


CANONICAL_FIELDS: list[str] = [
    "sku_local",
    "title",
    "brand",
    "model",
    "asin",
    "upc",
    "ean",
    "upc_ean_asin",
    "condition",
    "quantity",
    "est_cost_per_unit",
    "notes",
    "category_hint",
    "msrp",
    "color_size_variant",
    "lot_id",
]
