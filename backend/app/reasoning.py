LLM reasoning layer with Groq Mixtral model.

Prompt engineering principles applied here:
1. Role + scope constraint  - the model is told exactly what it is and is not
   allowed to do (narrate/judge given facts, never invent numbers).
2. Grounding via structured input - the model receives only a JSON block of
   pre-computed facts, so it cannot hallucinate stock levels or demand.
3. Few-shot examples - two worked examples show the desired tone, structure,
   and how confidence should change the language.
4. Output-format enforcement - the model must return strict JSON matching a
   schema, so the backend can parse it reliably without brittle regex.
5. Low temperature - reasoning about operational data should be consistent,
   not creative.
6. Chain-of-thought reasoning - model explains its logic before the final answer.
"""
import json
from groq import Groq
from app.config import settings

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


SYSTEM_PROMPT = """You are an expert inventory reorder analyst for a warehouse operations team.
Your role is to interpret pre-computed inventory metrics and communicate business implications clearly and specifically for each SKU.

## CONTEXT
You will receive a JSON object containing PRE-COMPUTED FACTS about one SKU (stock keeping unit).
All numerical forecasts, confidence levels, and urgency classifications have been calculated by a statistical engine.

## YOUR TASK
Produce a concise (2-4 sentence) JSON-formatted, action-oriented explanation that:
1. Begins by naming the product (`sku_name`) and stating the immediate status (e.g., "Stock covers X days").
2. Translates the metrics into operational language and justifies the `urgency` field ("critical", "order-soon", "watch").
3. Provides one clear, fact-bound operational action or monitoring step tied to the provided facts (for example: monitor daily sales for N days, prepare to place reorder, or confirm supplier lead-times). Do NOT invent or add numeric values not present in the input.
4. Points out product-specific risk factors or signals (lead time, volatility, external events) and explains low confidence when present.
5. Use varied phrasing so different SKUs produce clearly different reasoning — avoid repeating a single template for all SKUs.

## CRITICAL CONSTRAINTS
✗ NEVER invent, adjust, or recalculate any number
✗ NEVER override or contradict the "urgency" field
✗ NEVER make business recommendations beyond the provided facts
✓ ALWAYS cite specific numbers from the input (e.g., days_of_cover, lead_time_days)
✓ ALWAYS mention external signals if present (e.g., "due to storm")
✓ ALWAYS explain low confidence (either volatility or external factors)
✓ Format response as valid JSON only: {"reasoning": "<explanation>"}

## PROMPT ENGINEERING: FEW-SHOT EXAMPLES (show varied phrasing)

EXAMPLE 1 (Critical + Low Confidence):
Input: {"sku_name": "Rain Poncho (Adult)", "current_stock": 12, "daily_demand": 14.2, "lead_time_days": 10, "days_of_cover": 0.8, "days_until_breach": 0, "urgency": "critical", "confidence": "low", "external_signal": "storm"}
Output: {"reasoning": "Rain Poncho (Adult) has only 0.8 days of cover while lead time is 10 days — a stockout is imminent. Confidence is low because an incoming storm is driving demand above historical norms, which could deplete stock faster than the model anticipates."}

EXAMPLE 2 (Order-soon + Medium Confidence):
Input: {"sku_name": "Ceramic Coffee Mug - 12oz", "current_stock": 45, "daily_demand": 4.8, "lead_time_days": 7, "days_of_cover": 9.4, "days_until_breach": 2, "urgency": "order-soon", "confidence": "medium", "external_signal": null}
Output: {"reasoning": "Ceramic Coffee Mug - 12oz covers about 9.4 days of demand while lead time is 7 days, so breach is expected in ~2 days. Confidence is medium due to recent demand variation — monitor daily sales and be prepared to place a reorder if depletion accelerates."}

EXAMPLE 3 (Watch + High Confidence):
Input: {"sku_name": "USB-C Power Bank 10K", "current_stock": 310, "daily_demand": 9.4, "lead_time_days": 21, "days_of_cover": 33.0, "days_until_breach": 0, "urgency": "watch", "confidence": "high", "external_signal": null}
Output: {"reasoning": "USB-C Power Bank 10K has 33 days of cover against a 21-day lead time, giving a comfortable buffer. Demand is stable; continue routine monitoring and no immediate action is required."}

EXAMPLE 4 (Critical + High Confidence - supply issue):
Input: {"sku_name": "LED Bulb 9W", "current_stock": 5, "daily_demand": 2.0, "lead_time_days": 14, "days_of_cover": 2.5, "days_until_breach": 3, "urgency": "critical", "confidence": "high", "external_signal": "supplier_delay"}
Output: {"reasoning": "LED Bulb 9W has only 2.5 days of cover while lead time is 14 days, creating immediate stock risk. Confidence is high but an active supplier_delay increases delivery risk — confirm supplier timing and prioritize replenishment actions."}
"""


def generate_reasoning(facts: dict) -> tuple[str, str]:
    """
    Returns (reasoning_text, generated_by) where generated_by is 'llm' or
    'fallback' (used if the API call fails, so the demo never breaks).
    
    Uses Groq Mixtral model with optimized prompt engineering:
    - Structured few-shot examples for consistent output
    - JSON mode enforces structured output
    - Low temperature (0.2) ensures consistency over creativity
    - Explicit constraints prevent hallucination
    """
    try:
        client = get_client()
        completion = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.2,
            max_tokens=250,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze these inventory facts and provide reasoning in JSON format:\n\n{json.dumps(facts, indent=2)}"},
            ],
            response_format={"type": "json_object"},
        )
        raw = completion.choices[0].message.content
        parsed = json.loads(raw)
        reasoning = parsed.get("reasoning", "").strip()
        if not reasoning:
            raise ValueError("empty reasoning from model")
        return reasoning, "llm"
    except Exception as e:
        print(f"LLM call failed: {e}")
        return _fallback_reasoning(facts), "fallback"


def _fallback_reasoning(facts: dict) -> str:
    """Deterministic backup if the LLM call fails, so the live demo is never blocked on network/API issues."""
    if facts["urgency"] == "critical":
        text = (
            f"{facts.get('sku_name', 'This SKU')} covers about {facts['days_of_cover']} days at current demand while lead time is {facts['lead_time_days']} days — immediate stock risk exists."
        )
        text += " Action: prioritize confirming supplier timing and prepare replenishment steps."
    elif facts["urgency"] == "order-soon":
        text = (
            f"{facts.get('sku_name', 'This SKU')} will reach the reorder threshold in about {facts['days_until_breach']} day(s) given a {facts['lead_time_days']}-day lead time."
        )
        text += " Action: monitor daily sales and be ready to place an order if depletion accelerates."
    else:
        text = (
            f"{facts.get('sku_name', 'This SKU')} comfortably covers demand through the lead-time window. No immediate action required."
        )

    if facts.get("confidence") == "low":
        if facts.get("external_signal"):
            text += f" Confidence is low due to an active signal: {facts['external_signal']}."
            text += " Action: validate the external signal and increase monitoring frequency."
        else:
            text += " Confidence is low because demand is volatile. Action: monitor demand closely over the next few days."

    return text
