from pydantic import BaseModel, Field
from typing import Optional, Literal


class SKU(BaseModel):
    sku_id: str
    name: str
    category: str
    baseline_daily_demand: float
    seasonality: Literal["flat", "summer", "spring", "weather-reactive"]
    volatility: Literal["low", "medium", "high", "extreme"]
    lead_time_days: int
    unit_cost: float
    current_stock: int
    external_signal: Optional[str] = None  # e.g. "storm", "heatwave", None


class SalesRecord(BaseModel):
    sku_id: str
    day: int
    units_sold: int


class ForecastPoint(BaseModel):
    day: int
    forecast: float
    upper: float
    lower: float


class ForecastResult(BaseModel):
    sku_id: str
    mean_daily_demand: float
    std_dev: float
    coefficient_of_variation: float
    confidence: Literal["high", "medium", "low"]
    daily_trend: float
    points: list[ForecastPoint]


class ReorderReport(BaseModel):
    sku_id: str
    urgency: Literal["watch", "order-soon", "critical"]
    days_of_cover: float
    reorder_point: float
    suggested_qty: int
    estimated_cost: float
    reasoning: str
    confidence: Literal["high", "medium", "low"]
    generated_by: Literal["llm", "fallback"] = "llm"
