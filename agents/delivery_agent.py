"""
Delivery Agent (LLM-based) - Analyzes delivery timing and seller handoff.

Responsibilities:
- Provide raw timestamps to LLM.
- LLM extracts dates and outputs variances (using provided hints).
"""

import json
from datetime import datetime
from tools.data_loader import OlistDataLoader
from tools.llm_client import llm_json_call


DELIVERY_SYSTEM_PROMPT = """You are a Delivery Agent for an E-commerce Dispute Resolution System.
Your job is to analyze delivery dates and seller handoff times.

You will be given:
1. Raw order timestamps.
2. Raw item timestamps (for seller handoff analysis).
3. Pre-calculated variances in hours (HINTS - use these exactly to avoid datetime math errors).

Output a JSON object exactly matching this schema:
{
  "delivered_at": "<order_delivered_customer_date or null>",
  "estimated_delivery_at": "<order_estimated_delivery_date or null>",
  "carrier_handoff_at": "<order_delivered_carrier_date or null>",
  "delivery_variance_hours": <float or null, from hint>,
  "is_late_delivery": <boolean, true if delivery_variance_hours > 0>,
  "seller_handoff_analysis": [
    {
      "seller_id": "<seller_id>",
      "shipping_limit_at": "<shipping_limit_date>",
      "handoff_variance_hours": <float or null, from hint>,
      "is_late_handoff": <boolean, true if handoff_variance_hours > 0>
    }
  ],
  "late_handoff_seller_ids": ["<list of unique seller IDs where is_late_handoff is true>"]
}
"""

def _parse_dt(dt_str) -> datetime:
    """Helper to parse datetime strings safely."""
    if not dt_str or not isinstance(dt_str, str) or str(dt_str).lower() == "nan":
        return None
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _hours_between(t1: datetime, t2: datetime) -> float:
    """Helper to calculate hours between t1 and t2 (t1 - t2)."""
    if not t1 or not t2:
        return None
    return round((t1 - t2).total_seconds() / 3600.0, 2)


def run_delivery_agent(order_id: str, data: OlistDataLoader, items_raw: list = None) -> dict:
    """
    Analyze delivery variance using LLM with hints.
    """
    result = {
        "delivered_at": None,
        "estimated_delivery_at": None,
        "carrier_handoff_at": None,
        "delivery_variance_hours": None,
        "is_late_delivery": False,
        "seller_handoff_analysis": [],
        "late_handoff_seller_ids": []
    }

    order = data.get_order(order_id)
    if not order:
        return result

    # Calculate main delivery variance hint
    delivered = _parse_dt(order.get("order_delivered_customer_date"))
    estimated = _parse_dt(order.get("order_estimated_delivery_date"))
    carrier = _parse_dt(order.get("order_delivered_carrier_date"))
    
    delivery_variance = _hours_between(delivered, estimated)
    is_late_delivery = delivery_variance is not None and delivery_variance > 0

    # Calculate seller handoff hints
    seller_hints = {}
    if items_raw:
        for item in items_raw:
            sid = item.get("seller_id")
            if not sid:
                continue
            limit = _parse_dt(item.get("shipping_limit_date"))
            if sid not in seller_hints and limit and carrier:
                var = _hours_between(carrier, limit)
                seller_hints[sid] = {
                    "handoff_variance_hours": var,
                    "is_late_handoff": var is not None and var > 0
                }

    user_prompt = (
        f"Order ID: {order_id}\n\n"
        f"Order Data: {json.dumps(order)}\n\n"
        f"Items Data: {json.dumps(items_raw or [])}\n\n"
        f"HINTS (Use these for datetime math):\n"
        f"delivery_variance_hours = {delivery_variance}\n"
        f"seller_hints = {json.dumps(seller_hints)}\n"
    )

    print(f"  [DeliveryAgent-LLM] Calling LLM...")
    try:
        llm_result = llm_json_call(
            system_prompt=DELIVERY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=512
        )
        
        result.update({
            "delivered_at": llm_result.get("delivered_at"),
            "estimated_delivery_at": llm_result.get("estimated_delivery_at"),
            "carrier_handoff_at": llm_result.get("carrier_handoff_at"),
            "delivery_variance_hours": llm_result.get("delivery_variance_hours"),
            "is_late_delivery": bool(llm_result.get("is_late_delivery", False)),
            "seller_handoff_analysis": llm_result.get("seller_handoff_analysis", []),
            "late_handoff_seller_ids": llm_result.get("late_handoff_seller_ids", []),
        })
    except Exception as e:
        print(f"  [DeliveryAgent-LLM] LLM call failed: {e}. Falling back to deterministic.")
        # Minimal fallback
        result["delivered_at"] = order.get("order_delivered_customer_date")
        result["estimated_delivery_at"] = order.get("order_estimated_delivery_date")
        result["carrier_handoff_at"] = order.get("order_delivered_carrier_date")
        result["delivery_variance_hours"] = delivery_variance
        result["is_late_delivery"] = is_late_delivery
        
        if items_raw:
            seen_sellers = set()
            for item in items_raw:
                sid = item.get("seller_id")
                if sid and sid not in seen_sellers:
                    seen_sellers.add(sid)
                    hint = seller_hints.get(sid, {})
                    var = hint.get("handoff_variance_hours")
                    is_late = hint.get("is_late_handoff", False)
                    result["seller_handoff_analysis"].append({
                        "seller_id": sid,
                        "shipping_limit_at": item.get("shipping_limit_date"),
                        "handoff_variance_hours": var,
                        "is_late_handoff": is_late
                    })
                    if is_late:
                        result["late_handoff_seller_ids"].append(sid)

    print(f"  [DeliveryAgent-LLM] delivered={result['delivered_at']}, "
          f"estimated={result['estimated_delivery_at']}, "
          f"variance_hours={result['delivery_variance_hours']}, "
          f"late={result['is_late_delivery']}, "
          f"late_sellers={result['late_handoff_seller_ids']}")

    return result
