"""
Deterministic forecasting engine.

Deliberately kept LLM-free: the numeric forecast must be reproducible and
auditable. The LLM's job (see reasoning.py) is to explain these numbers in
plain English and make a judgment call, not to compute them.
"""
import math
from app.schemas import ForecastPoint, ForecastResult, SKU


def compute_forecast(sku: SKU, history: list[dict], horizon_days: int = 14) -> ForecastResult:
    recent = history[-21:] if len(history) >= 21 else history
    units = [r["units_sold"] for r in recent]

    mean = sum(units) / len(units)
    variance = sum((u - mean) ** 2 for u in units) / len(units)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean if mean else 0.0

    trend_window = units[-7:] if len(units) >= 7 else units
    daily_trend = (trend_window[-1] - trend_window[0]) / max(1, len(trend_window))

    signal_boost = 1.4 if sku.external_signal else 1.0

    last_day = history[-1]["day"] if history else 0
    points: list[ForecastPoint] = []
    base = mean
    for i in range(1, horizon_days + 1):
        base = base + daily_trend * signal_boost
        spread = std_dev * signal_boost * math.sqrt(i / 3)
        points.append(ForecastPoint(
            day=last_day + i,
            forecast=max(0.0, round(base, 1)),
            upper=max(0.0, round(base + spread, 1)),
            lower=max(0.0, round(base - spread, 1)),
        ))

    if cv > 0.35 or sku.external_signal:
        confidence = "low"
    elif cv > 0.18:
        confidence = "medium"
    else:
        confidence = "high"

    return ForecastResult(
        sku_id=sku.sku_id,
        mean_daily_demand=round(mean, 2),
        std_dev=round(std_dev, 2),
        coefficient_of_variation=round(cv, 3),
        confidence=confidence,
        daily_trend=round(daily_trend, 2),
        points=points,
    )


def compute_reorder_facts(sku: SKU, forecast: ForecastResult) -> dict:
    """
    Produces the structured numeric facts that get handed to the LLM.
    The LLM never invents these numbers -- it only narrates and judges them.
    """
    daily_demand = max(1.0, forecast.mean_daily_demand + forecast.daily_trend)
    days_of_cover = sku.current_stock / daily_demand

    safety_buffer = {"low": 1.5, "medium": 1.2, "high": 1.0}[forecast.confidence]
    reorder_point = daily_demand * sku.lead_time_days * safety_buffer
    will_breach = sku.current_stock < reorder_point
    days_until_breach = max(0, round(days_of_cover - sku.lead_time_days))

    if will_breach and days_until_breach <= 3:
        urgency = "critical"
    elif will_breach:
        urgency = "order-soon"
    else:
        urgency = "watch"

    suggested_qty = round(daily_demand * sku.lead_time_days * safety_buffer * 1.3)

    return {
        "sku_id": sku.sku_id,
        "sku_name": sku.name,
        "category": sku.category,
        "current_stock": sku.current_stock,
        "daily_demand": round(daily_demand, 1),
        "lead_time_days": sku.lead_time_days,
        "days_of_cover": round(days_of_cover, 1),
        "reorder_point": round(reorder_point, 1),
        "days_until_breach": days_until_breach,
        "urgency": urgency,
        "confidence": forecast.confidence,
        "coefficient_of_variation": forecast.coefficient_of_variation,
        "external_signal": sku.external_signal,
        "suggested_qty": suggested_qty,
        "estimated_cost": round(suggested_qty * sku.unit_cost, 2),
    }
