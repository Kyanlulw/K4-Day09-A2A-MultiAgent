"""
Customer Agent (LLM-based) - Identifies customer identity and order history.

Responsibilities:
- Lookup customer by customer_id from the order (using DataLoader to fetch raw data)
- Provide raw data to LLM to extract customer_unique_id and related orders.
"""

import json
from tools.data_loader import OlistDataLoader
from tools.llm_client import llm_json_call


CUSTOMER_SYSTEM_PROMPT = """You are a Customer Agent for an E-commerce Dispute Resolution System.
Your job is to extract customer information from raw data.

You will be given:
1. The requested order_id.
2. Raw customer data (customer_id, customer_unique_id).
3. A list of ALL related orders for this customer_unique_id.

You must output a JSON object exactly matching this schema:
{
  "customer_unique_id": "<the customer_unique_id, or null if missing>",
  "related_order_ids": ["<list of up to 5 order IDs that are NOT the current order_id>"]
}

Rules:
- related_order_ids MUST NOT include the current order_id.
- limit related_order_ids to maximum 5 items.
"""


def run_customer_agent(order_id: str, data: OlistDataLoader) -> dict:
    """
    Analyze customer identity and purchase history using LLM.
    """
    result = {
        "customer_unique_id": None,
        "related_order_ids": [],
    }

    # Fetch raw data
    order = data.get_order(order_id)
    if not order:
        print(f"  [CustomerAgent-LLM] Order {order_id} not found!")
        return result

    customer_id = order.get("customer_id")
    if not customer_id or customer_id == "nan":
        print(f"  [CustomerAgent-LLM] No customer_id for order {order_id}")
        return result

    customer = data.get_customer(customer_id)
    if not customer:
        print(f"  [CustomerAgent-LLM] Customer {customer_id} not found!")
        return result

    customer_unique_id = customer.get("customer_unique_id")
    all_related_orders = data.get_related_orders(customer_unique_id, exclude_order_id="") # LLM should exclude it

    # Build prompt
    user_prompt = (
        f"Current order_id: {order_id}\n\n"
        f"Raw customer data: {json.dumps(customer)}\n\n"
        f"All related orders: {json.dumps(all_related_orders)}"
    )

    print(f"  [CustomerAgent-LLM] Calling LLM...")
    try:
        llm_result = llm_json_call(
            system_prompt=CUSTOMER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=256
        )
        
        result["customer_unique_id"] = llm_result.get("customer_unique_id")
        # Ensure the list excludes current order_id and has max 5
        rel_orders = [o for o in llm_result.get("related_order_ids", []) if o != order_id]
        result["related_order_ids"] = rel_orders[:5]
        
    except Exception as e:
        print(f"  [CustomerAgent-LLM] LLM call failed: {e}. Falling back to deterministic.")
        result["customer_unique_id"] = customer_unique_id
        result["related_order_ids"] = [o for o in all_related_orders if o != order_id][:5]

    is_repeat = len(result["related_order_ids"]) > 0
    print(f"  [CustomerAgent-LLM] customer_unique_id={result['customer_unique_id']}, "
          f"related_orders={len(result['related_order_ids'])}, "
          f"repeat_customer={is_repeat}")

    return result
