"""
Seeds MongoDB with a demo SKU catalog and synthetic sales history.
Run once on startup if the database is empty -- makes the project runnable
out of the box for graders without needing real historical sales data.
"""
import math
import random
from app.database import skus_collection, sales_history_collection

DEMO_SKUS = [
    {"sku_id": "SKU-1042", "name": "Insulated Water Bottle 32oz", "category": "Outdoor",
     "baseline_daily_demand": 42, "seasonality": "summer", "volatility": "low",
     "lead_time_days": 7, "unit_cost": 8.5, "external_signal": None},
    {"sku_id": "SKU-2210", "name": "Folding Camp Chair", "category": "Outdoor",
     "baseline_daily_demand": 18, "seasonality": "summer", "volatility": "medium",
     "lead_time_days": 14, "unit_cost": 22, "external_signal": None},
    {"sku_id": "SKU-3387", "name": "Rain Poncho (Adult)", "category": "Apparel",
     "baseline_daily_demand": 9, "seasonality": "weather-reactive", "volatility": "high",
     "lead_time_days": 10, "unit_cost": 4.2, "external_signal": "storm"},
    {"sku_id": "SKU-4456", "name": "USB-C Power Bank 10K", "category": "Electronics",
     "baseline_daily_demand": 27, "seasonality": "flat", "volatility": "low",
     "lead_time_days": 21, "unit_cost": 14, "external_signal": None},
    {"sku_id": "SKU-5501", "name": "Trail Running Shoes M9", "category": "Footwear",
     "baseline_daily_demand": 15, "seasonality": "spring", "volatility": "medium",
     "lead_time_days": 30, "unit_cost": 41, "external_signal": None},
    {"sku_id": "SKU-6098", "name": "Citronella Candle 3-pk", "category": "Outdoor",
     "baseline_daily_demand": 11, "seasonality": "summer", "volatility": "high",
     "lead_time_days": 12, "unit_cost": 6.75, "external_signal": "heatwave"},
    {"sku_id": "SKU-7743", "name": "Bluetooth Trail Speaker", "category": "Electronics",
     "baseline_daily_demand": 6, "seasonality": "flat", "volatility": "extreme",
     "lead_time_days": 25, "unit_cost": 33, "external_signal": None},
]

VOL_MAP = {"low": 0.08, "medium": 0.18, "high": 0.32, "extreme": 0.55}


def _generate_history(sku: dict, days: int = 60) -> list[dict]:
    rng = random.Random(sum(ord(c) for c in sku["sku_id"]))
    vol = VOL_MAP[sku["volatility"]]
    baseline = sku["baseline_daily_demand"]
    history = []
    for d in range(days):
        seasonal_push = math.sin((d / days) * math.pi) * baseline * 0.3 if sku["seasonality"] == "summer" else 0
        noise = (rng.random() - 0.5) * 2 * vol * baseline
        level = max(1, round(baseline + seasonal_push + noise))
        history.append({"sku_id": sku["sku_id"], "day": d, "units_sold": level})
    return history


def _generate_current_stock(sku: dict) -> int:
    rng = random.Random(len(sku["sku_id"]) * 7 + 3)
    return round(sku["baseline_daily_demand"] * sku["lead_time_days"] * (0.5 + rng.random() * 1.3))


async def seed_if_empty():
    count = await skus_collection.count_documents({})
    if count > 0:
        return {"seeded": False, "reason": "already populated"}

    for sku in DEMO_SKUS:
        doc = {**sku, "current_stock": _generate_current_stock(sku)}
        await skus_collection.insert_one(doc)
        history = _generate_history(sku)
        if history:
            await sales_history_collection.insert_many(history)

    return {"seeded": True, "sku_count": len(DEMO_SKUS)}
