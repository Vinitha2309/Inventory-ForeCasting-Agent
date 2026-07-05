import math
import random

from app.database import reports_collection, sales_history_collection, skus_collection
from app.forecasting import compute_forecast, compute_reorder_facts
from app.reasoning import generate_reasoning
from app.schemas import SKU

VOL_MAP = {
    "low": 0.08,
    "medium": 0.18,
    "high": 0.32,
    "extreme": 0.55,
}


def _generate_history(sku: SKU, days: int = 60) -> list[dict]:
    rng = random.Random(sum(ord(c) for c in sku.sku_id))
    vol = VOL_MAP[sku.volatility]
    baseline = sku.baseline_daily_demand
    history = []

    for d in range(days):
        seasonal_push = (
            math.sin((d / days) * math.pi) * baseline * 0.3
            if sku.seasonality == "summer"
            else 0
        )
        noise = (rng.random() - 0.5) * 2 * vol * baseline
        level = max(1, round(baseline + seasonal_push + noise))
        history.append({"sku_id": sku.sku_id, "day": d, "units_sold": level})

    return history


async def create_sku(sku: SKU) -> dict:
    existing = await skus_collection.find_one({"sku_id": sku.sku_id})
    if existing:
        raise ValueError(f"SKU with id '{sku.sku_id}' already exists")

    document = sku.model_dump()
    await skus_collection.insert_one(document)

    history = _generate_history(sku)
    if history:
        await sales_history_collection.insert_many(history)

    forecast = compute_forecast(sku, history)
    facts = compute_reorder_facts(sku, forecast)
    llm_facts = {k: v for k, v in facts.items() if k != "sku_id"}
    reasoning_text, generated_by = generate_reasoning(llm_facts)

    report = {
        "sku_id": sku.sku_id,
        "urgency": facts["urgency"],
        "days_of_cover": facts["days_of_cover"],
        "reorder_point": facts["reorder_point"],
        "suggested_qty": facts["suggested_qty"],
        "estimated_cost": facts["estimated_cost"],
        "confidence": facts["confidence"],
        "reasoning": reasoning_text,
        "generated_by": generated_by,
    }

    await reports_collection.update_one(
        {"sku_id": sku.sku_id}, {"$set": report}, upsert=True
    )

    return {"sku": document, "report": report}
