from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import skus_collection, sales_history_collection, reports_collection, ensure_indexes
from app.products import create_sku
from app.schemas import SKU
from app.forecasting import compute_forecast, compute_reorder_facts
from app.reasoning import generate_reasoning
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    await seed_if_empty()
    yield


app = FastAPI(title="StockWatch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/skus")
async def list_skus():
    """Returns every SKU with its live urgency/reasoning report (cached in Mongo, regenerated on demand)."""
    skus = await skus_collection.find({}, {"_id": 0}).to_list(length=200)
    results = []
    for sku_doc in skus:
        report = await _get_or_build_report(sku_doc)
        results.append({"sku": sku_doc, "report": report})

    order = {"critical": 0, "order-soon": 1, "watch": 2}
    results.sort(key=lambda r: order.get(r["report"]["urgency"], 3))
    return results


@app.get("/api/skus/{sku_id}")
async def get_sku_detail(sku_id: str):
    sku_doc = await skus_collection.find_one({"sku_id": sku_id}, {"_id": 0})
    if not sku_doc:
        raise HTTPException(status_code=404, detail="SKU not found")

    history = await sales_history_collection.find(
        {"sku_id": sku_id}, {"_id": 0}
    ).sort("day", 1).to_list(length=500)

    sku = SKU(**sku_doc)
    forecast = compute_forecast(sku, history)
    report = await _get_or_build_report(sku_doc, force_refresh=True)

    return {
        "sku": sku_doc,
        "history": history,
        "forecast": forecast.model_dump(),
        "report": report,
    }


@app.post("/api/skus")
async def add_sku(sku: SKU):
    try:
        result = await create_sku(sku)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/skus/{sku_id}/refresh")
async def refresh_report(sku_id: str):
    """Forces a fresh LLM call, bypassing the cached report -- useful for demoing the live reasoning."""
    sku_doc = await skus_collection.find_one({"sku_id": sku_id}, {"_id": 0})
    if not sku_doc:
        raise HTTPException(status_code=404, detail="SKU not found")
    report = await _get_or_build_report(sku_doc, force_refresh=True)
    return report


async def _get_or_build_report(sku_doc: dict, force_refresh: bool = False) -> dict:
    sku_id = sku_doc["sku_id"]

    if not force_refresh:
        cached = await reports_collection.find_one({"sku_id": sku_id}, {"_id": 0})
        if cached:
            return cached

    history = await sales_history_collection.find(
        {"sku_id": sku_id}, {"_id": 0}
    ).sort("day", 1).to_list(length=500)

    sku = SKU(**sku_doc)
    forecast = compute_forecast(sku, history)
    facts = compute_reorder_facts(sku, forecast)

    llm_facts = {k: v for k, v in facts.items() if k not in ("sku_id",)}
    reasoning_text, generated_by = generate_reasoning(llm_facts)

    report = {
        "sku_id": sku_id,
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
        {"sku_id": sku_id}, {"$set": report}, upsert=True
    )
    return report
