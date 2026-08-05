"""
Order & Product Agent (LLM-based) - Analyzes order items, sellers, products.

Responsibilities:
- Provide raw item, seller, product data to LLM.
- LLM extracts IDs, category names, and outputs total prices (aided by hints).
"""

import json
from tools.data_loader import OlistDataLoader
from tools.llm_client import llm_json_call


ORDER_PRODUCT_SYSTEM_PROMPT = """You are an Order & Product Agent for an E-commerce Dispute Resolution System.
Your job is to analyze raw item rows and extract structured information.

You will be given:
1. Raw item data.
2. Raw product category data.
3. Pre-calculated totals (use these to avoid math errors).

Output a JSON object exactly matching this schema:
{
  "has_items": <boolean>,
  "item_ids": ["<list of item IDs like order_id:order_item_id>"],
  "seller_ids": ["<list of unique seller IDs>"],
  "product_ids": ["<list of unique product IDs>"],
  "category_names": ["<list of unique product_category_name>"],
  "item_total_brl": <float sum of all price fields, use pre-calculated hint>,
  "freight_total_brl": <float sum of all freight_value fields, use pre-calculated hint>,
  "expected_total_brl": <float sum of item_total_brl + freight_total_brl, use pre-calculated hint>
}

Rules:
- item_ids limit: 5
- seller_ids limit: 3
- product_ids limit: 5
- category_names limit: 5
- Ensure uniqueness for seller_ids, product_ids, category_names.
"""


def run_order_product_agent(order_id: str, data: OlistDataLoader) -> dict:
    """
    Analyze order items, sellers, products using LLM.
    """
    result = {
        "has_items": False,
        "items_raw": [],
        "item_ids": [],
        "seller_ids": [],
        "product_ids": [],
        "category_names": [],
        "item_total_brl": 0.0,
        "freight_total_brl": 0.0,
        "expected_total_brl": 0.0,
    }

    items = data.get_items(order_id)
    if not items:
        print(f"  [OrderProductAgent-LLM] No items found for order {order_id}")
        return result

    result["has_items"] = True
    result["items_raw"] = items

    # Pre-calculate totals as hints to prevent LLM math hallucinations
    calc_item_total = sum(float(item.get("price", 0) or 0) for item in items)
    calc_freight_total = sum(float(item.get("freight_value", 0) or 0) for item in items)
    calc_expected_total = calc_item_total + calc_freight_total

    # Fetch product categories
    categories = []
    for item in items:
        pid = item.get("product_id")
        if pid:
            prod = data.get_product(pid)
            if prod:
                cat = prod.get("product_category_name")
                if cat and cat != "nan":
                    categories.append({"product_id": pid, "category": cat})

    user_prompt = (
        f"Order ID: {order_id}\n\n"
        f"Raw Items: {json.dumps(items)}\n\n"
        f"Product Categories: {json.dumps(categories)}\n\n"
        f"HINTS (Use these for the math fields):\n"
        f"item_total_brl = {calc_item_total:.2f}\n"
        f"freight_total_brl = {calc_freight_total:.2f}\n"
        f"expected_total_brl = {calc_expected_total:.2f}\n"
    )

    print(f"  [OrderProductAgent-LLM] Calling LLM...")
    try:
        llm_result = llm_json_call(
            system_prompt=ORDER_PRODUCT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=512
        )
        
        result.update({
            "item_ids": llm_result.get("item_ids", [])[:5],
            "seller_ids": llm_result.get("seller_ids", [])[:3],
            "product_ids": llm_result.get("product_ids", [])[:5],
            "category_names": llm_result.get("category_names", [])[:5],
            "item_total_brl": round(float(llm_result.get("item_total_brl", calc_item_total)), 2),
            "freight_total_brl": round(float(llm_result.get("freight_total_brl", calc_freight_total)), 2),
            "expected_total_brl": round(float(llm_result.get("expected_total_brl", calc_expected_total)), 2),
        })
    except Exception as e:
        print(f"  [OrderProductAgent-LLM] LLM call failed: {e}. Falling back to deterministic.")
        # Minimal fallback
        result["item_ids"] = [f"{order_id}:{item.get('order_item_id')}" for item in items][:5]
        result["seller_ids"] = list(set([item.get('seller_id') for item in items if item.get('seller_id')]))[:3]
        result["product_ids"] = list(set([item.get('product_id') for item in items if item.get('product_id')]))[:5]
        result["category_names"] = list(set([c["category"] for c in categories]))[:5]
        result["item_total_brl"] = round(calc_item_total, 2)
        result["freight_total_brl"] = round(calc_freight_total, 2)
        result["expected_total_brl"] = round(calc_expected_total, 2)

    print(f"  [OrderProductAgent-LLM] items={len(items)}, "
          f"sellers={len(result['seller_ids'])}, "
          f"products={len(result['product_ids'])}, "
          f"categories={len(result['category_names'])}, "
          f"expected_total={result['expected_total_brl']}")

    return result
